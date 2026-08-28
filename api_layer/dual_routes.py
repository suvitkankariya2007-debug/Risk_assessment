import re
import time
import uuid
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from schemas.data_models import (
    ChatRequest,
    ChatResponse,
    SlotExtractionResult,
    DeterministicContextPayload,
    PersonaType,
    AssetNode,
    EPSSInput,
    EPSSOutput,
    FAIRInput,
    FAIROutput,
    XAIInput,
    XAIOutput,
    MILPROSIInput,
    MILPROSIOutput,
    ComplianceControl,
)
from core_engines.epss_model import EPSSPredictor
from core_engines.topology_graph import AssetTopologyGraph
from core_engines.fair_model import FAIRRiskEngine
from core_engines.xai_trust import XAITrustAuditor
from core_engines.rosi_optimizer import ROSIOptimizer
from core_engines.retraining_bus import ContinuousRetrainingBus
from api_layer.synthesizer import PromptSynthesizers, DeterministicExecutionAggregator
from api_layer.guardrails import SanityGuardrailVerifier


router = APIRouter()
epss_predictor = EPSSPredictor()
asset_graph = AssetTopologyGraph()
fair_engine = FAIRRiskEngine()
xai_auditor = XAITrustAuditor()
rosi_optimizer = ROSIOptimizer()
retraining_bus = ContinuousRetrainingBus()
synthesizers = PromptSynthesizers()
guardrail = SanityGuardrailVerifier()


class IntentClassifier:
    VENDOR_PATTERNS = re.compile(
        r"\b(microsoft|ibm|adobe|hp|apache|google|apple)\b", re.IGNORECASE
    )
    CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)
    BUDGET_PATTERN = re.compile(r"(?<!\bCVE-)(\d+(?:\.\d+)?)\s*(crores?|cr|lakhs?|l|rs|inr)\b", re.IGNORECASE)
    TIMELINE_PATTERN = re.compile(r"(\d+)\s*(days?|d|weeks?|w|hours?|h)", re.IGNORECASE)

    def classify(self, prompt: str) -> str:
        p = prompt.lower()
        if any(k in p for k in ["fix", "patch", "remediate", "mitigate", "control", "waf", "vpn", "mfa"]):
            return "remediation"
        if any(k in p for k in ["score", "risk", "how risky", "impact", "loss", "eal", "fair"]):
            return "risk_assessment"
        if any(k in p for k in ["compliance", "sebi", "rbi", "audit", "framework"]):
            return "compliance"
        return "general"


class SlotExtractor:
    def extract(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> SlotExtractionResult:
        cve_match = IntentClassifier.CVE_PATTERN.search(prompt)
        cve_id = cve_match.group(0).upper() if cve_match else None

        asset = None
        if context and "asset_target" in context:
            asset = context["asset_target"]
        else:
            for candidate in ["Core Payment Switch", "Customer DB", "API Gateway", "payment switch", "customer database", "api gateway"]:
                if candidate.lower() in prompt.lower():
                    asset = candidate
                    break

        budget = None
        bm = IntentClassifier.BUDGET_PATTERN.search(prompt)
        if bm:
            val = float(bm.group(1))
            unit = (bm.group(2) or "").lower()
            if unit.startswith("cr"):
                budget = val * 100.0
            elif unit.startswith("l"):
                budget = val
            else:
                budget = val

        timeline = None
        tm = IntentClassifier.TIMELINE_PATTERN.search(prompt)
        if tm:
            val = int(tm.group(1))
            unit = (tm.group(2) or "").lower()
            if unit.startswith("w"):
                timeline = val * 7
            elif unit.startswith("h"):
                timeline = max(1, val // 24)
            else:
                timeline = val

        return SlotExtractionResult(
            asset_target=asset,
            cve_id=cve_id,
            budget_limit=budget,
            timeline_delta=timeline,
            confidence=0.85 if (asset or cve_id) else 0.4,
        )


def _resolve_asset(slots: SlotExtractionResult) -> Optional[AssetNode]:
    if not slots.asset_target:
        return None
    return asset_graph.resolve(slots.asset_target)


def _build_epss(slots: SlotExtractionResult) -> Optional[EPSSOutput]:
    if not slots.cve_id:
        return None
    entry = next((e for e in retraining_bus.get_buffer() if e["cve_id"] == slots.cve_id), None)
    if entry:
        epss_in = EPSSInput(
            cve_id=entry["cve_id"],
            vendor=entry.get("vendor"),
            reference_count=entry.get("reference_count", 0),
            tags=entry.get("tags", []),
            exploit_poc_published=entry.get("exploit_poc_published", False),
            weaponized=entry.get("weaponized", False),
        )
    else:
        epss_in = EPSSInput(cve_id=slots.cve_id)
    return epss_predictor.predict(epss_in)


def _build_fair(asset: Optional[AssetNode], epss: Optional[EPSSOutput], slots: SlotExtractionResult) -> Optional[FAIROutput]:
    if not asset or not epss:
        return None
    trial_count = 10000
    if slots.timeline_delta is not None:
        trial_count = min(50000, max(1000, slots.timeline_delta * 500))
    fair_in = FAIRInput(
        asset=asset,
        p_exploit=epss.p_exploit,
        susceptibility=0.8,
        trial_count=trial_count,
        secondary_lef=0.3,
    )
    return fair_engine.run(fair_in)


def _build_xai(text: str, slots: SlotExtractionResult) -> XAIOutput:
    ref = f"CVSS v3.1 assessment for {slots.cve_id or 'vulnerability'}"
    tokens = re.findall(r"\b[A-Z]{2,}\b", text) or ["exploit", "remote", "code_execution"]
    return xai_auditor.audit(XAIInput(generated_text=text, reference_text=ref, salient_tokens=tokens))


def _build_milprosi(asset: Optional[AssetNode], fair: Optional[FAIROutput], slots: SlotExtractionResult) -> Optional[MILPROSIOutput]:
    if not fair or not asset:
        return None
    risk_reduced = fair.eal_inr_cr * 0.75
    control_cost = fair.eal_inr_cr * 0.20
    if slots.budget_limit is not None:
        control_cost = min(control_cost, slots.budget_limit)
    return rosi_optimizer.optimize(
        MILPROSIInput(
            control_cost_inr_cr=control_cost,
            eal_inr_cr=fair.eal_inr_cr,
            risk_reduced_inr_cr=risk_reduced,
        )
    )


def _compliance_controls(asset: Optional[AssetNode]) -> list:
    if not asset:
        return []
    return [
        ComplianceControl(control_id="C-001", pillar="Identify", description="Asset inventory and criticality scoring", slo_hours=24, rbi_category="Asset Management"),
        ComplianceControl(control_id="C-002", pillar="Protect", description="Encryption at rest and in transit", slo_hours=48, rbi_category="Data Protection"),
        ComplianceControl(control_id="C-003", pillar="Detect", description="IDS/IPS and anomaly detection", slo_hours=4, rbi_category="Detection"),
        ComplianceControl(control_id="C-004", pillar="Respond", description="Incident response playbook", slo_hours=1, rbi_category="Response"),
        ComplianceControl(control_id="C-005", pillar="Recover", description="Backup and restoration SLA", slo_hours=72, rbi_category="Recovery"),
    ]


@router.post("/chat/business", response_model=ChatResponse)
async def chat_business(request: ChatRequest) -> ChatResponse:
    return await _process_chat(request)


@router.post("/chat/technical", response_model=ChatResponse)
async def chat_technical(request: ChatRequest) -> ChatResponse:
    return await _process_chat(request)


async def _process_chat(request: ChatRequest) -> ChatResponse:
    start = time.perf_counter()
    classifier = IntentClassifier()
    extractor = SlotExtractor()
    intent = classifier.classify(request.prompt)
    slots = extractor.extract(request.prompt, context=request.context_overrides)

    asset = _resolve_asset(slots)
    epss = _build_epss(slots)
    fair = _build_fair(asset, epss, slots)

    xai = _build_xai(request.prompt, slots)
    milprosi = _build_milprosi(asset, fair, slots)
    controls = _compliance_controls(asset)

    aggregator = DeterministicExecutionAggregator()
    payload = aggregator.aggregate(
        session_id=request.session_id,
        persona=request.persona,
        slots=slots,
        asset=asset,
        epss=epss,
        fair=fair,
        xai=xai,
        milprosi=milprosi,
        compliance_controls=controls,
    )

    formatted = synthesizers.synthesize(payload)
    passed, errors = guardrail.verify(payload, formatted)
    if not passed:
        payload.guardrail_passed = False
        payload.guardrail_errors = errors

    latency = (time.perf_counter() - start) * 1000.0
    return ChatResponse(
        session_id=request.session_id,
        persona=request.persona,
        formatted_output=formatted,
        context_payload=payload,
        latency_ms=round(latency, 2),
    )
