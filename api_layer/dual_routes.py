"""
api_layer/dual_routes.py
========================
FastAPI Router for CyberRiskIQ Gateway.

Endpoints:
- POST /api/v1/chat/business
- POST /api/v1/chat/technical
- POST /api/v1/models/stream-update
"""
import re
import time
import uuid
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Body

from schemas.data_models import (
    ChatRequest,
    ChatResponse,
    PersonaType,
    ThreatContext,
    EPSSPrediction,
    FAIRSimulationResult,
    XAITrustResult,
    ROSIOptimizationResult,
    ExecutionPayload,
    DeterministicContextPayload,
    SlotExtractionResult,
    AssetNode,
    EPSSOutput,
    FAIROutput,
    XAIOutput,
    MILPROSIOutput,
)
from core_engines.epss_model import EPSSPredictor
from core_engines.topology_graph import AssetTopologyGraph
from core_engines.fair_model import FAIRRiskEngine
from core_engines.xai_trust import XAITrustAuditor
from core_engines.rosi_optimizer import ROSIOptimizer
from api_layer.synthesizer import (
    format_business_briefing,
    format_technical_diagnostic,
    HybridSynthesizer,
)
from api_layer.guardrails import SanityGuardrailVerifier
from api_layer import mock_kb

router = APIRouter()

# Singletons for core engines
epss_predictor = EPSSPredictor()
asset_graph = AssetTopologyGraph()
fair_engine = FAIRRiskEngine()
xai_auditor = XAITrustAuditor()
rosi_optimizer = ROSIOptimizer()

synthesizer = HybridSynthesizer()
guardrail = SanityGuardrailVerifier()

_CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)
_BUDGET_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(crores?|cr|lakhs?|l)\b", re.IGNORECASE)


def _extract_slots(prompt: str) -> Dict[str, Any]:
    cve_match = _CVE_PATTERN.search(prompt)
    cve_id = cve_match.group(0).upper() if cve_match else "CVE-2024-1234"

    budget_lakhs = 300.0  # default control cost: ₹3.0 Cr = 300 Lakhs
    bm = _BUDGET_PATTERN.search(prompt)
    if bm:
        val = float(bm.group(1))
        unit = bm.group(2).lower()
        if unit.startswith("cr"):
            budget_lakhs = val * 100.0
        else:
            budget_lakhs = val

    # Resolve target asset name
    asset_name = "Core Payment Switch"
    for candidate in ["customer_db", "api_gateway", "core_payment_switch", "payment switch", "customer database", "api gateway"]:
        if candidate in prompt.lower():
            asset_name = candidate
            break

    return {
        "cve_id": cve_id,
        "asset_name": asset_name,
        "budget_lakhs": budget_lakhs,
    }


def _run_core_engines(prompt: str, context_overrides: Optional[Dict[str, Any]] = None) -> ExecutionPayload:
    """Execute Developer A deterministic math engines and build frozen ExecutionPayload."""
    slots = _extract_slots(prompt)
    if context_overrides:
        slots.update(context_overrides)

    # 1. Resolve Asset Topology
    try:
        topo_data = asset_graph.resolve_asset(slots["asset_name"])
    except KeyError:
        topo_data = asset_graph.resolve_asset("core_payment_switch")

    vuln_info = mock_kb.lookup_vuln(slots["cve_id"])

    # Build EPSS 16-feature boolean flags dictionary
    features: Dict[str, bool] = {
        "vend_microsoft": vuln_info["vendor"].lower() == "microsoft",
        "vend_ibm": vuln_info["vendor"].lower() == "ibm",
        "vend_adobe": vuln_info["vendor"].lower() == "adobe",
        "vend_hp": vuln_info["vendor"].lower() == "hp",
        "vend_apache": vuln_info["vendor"].lower() == "apache",
        "vend_google": vuln_info["vendor"].lower() == "google",
        "vend_apple": vuln_info["vendor"].lower() == "apple",
        "exp_weaponized": vuln_info["exploit_weaponized"],
        "exp_poc_published": vuln_info["poc_published"],
        "tag_code_execution": "code_execution" in vuln_info["tags"],
        "tag_remote": "remote" in vuln_info["tags"],
        "tag_denial_of_service": "dos" in vuln_info["tags"],
        "tag_web": "web" in vuln_info["tags"],
        "tag_memory_corruption": "memory_corruption" in vuln_info["tags"],
        "tag_local": "local" in vuln_info["tags"],
    }

    threat_context = ThreatContext(
        cve_id=slots["cve_id"],
        description=vuln_info["description"],
        asset_name=topo_data["asset_name"],
        asset_replacement_cost_cr=topo_data["asset_replacement_cost_cr"],
        daily_revenue_impact_cr=topo_data["daily_revenue_impact_cr"],
        regulatory_tier=topo_data["regulatory_tier"],
        cvss_base_score=9.8,
        cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        features=features,
        ref_count=vuln_info["reference_count"],
        proposed_control_cost_lakhs=slots["budget_lakhs"],
    )

    # 2. EPSS Predictor
    epss_prediction = epss_predictor.predict_probability(
        features=features,
        ref_count=threat_context.ref_count,
        cve_id=threat_context.cve_id,
    )

    # 3. FAIR Risk Engine
    fair_result = fair_engine.run_monte_carlo(
        epss_prob=epss_prediction.epss_probability,
        asset_replacement_cost_cr=threat_context.asset_replacement_cost_cr,
        daily_revenue_impact_cr=threat_context.daily_revenue_impact_cr,
        regulatory_tier=threat_context.regulatory_tier,
        iterations=10_000,
    )

    # 4. XAI Trust Auditor
    salient_tokens = [t for t in vuln_info["tags"]] + ["remote", "code_execution", "unauthenticated"]
    xai_trust = xai_auditor.evaluate_trust_score(
        description=threat_context.description,
        salient_tokens=salient_tokens,
    )

    # 5. ROSI Optimizer
    rosi_result = rosi_optimizer.evaluate_investment(
        eal_cr=fair_result.expected_annual_loss_cr,
        control_cost_lakhs=threat_context.proposed_control_cost_lakhs,
        risk_reduction_pct=85.0,
    )

    return ExecutionPayload(
        threat_context=threat_context,
        epss_prediction=epss_prediction,
        fair_result=fair_result,
        xai_trust=xai_trust,
        rosi_result=rosi_result,
    )


def _build_context_payload(payload: ExecutionPayload, session_id: str, persona: PersonaType) -> DeterministicContextPayload:
    """Build Developer B DeterministicContextPayload from ExecutionPayload."""
    asset_node = AssetNode(
        asset_id="AST-001",
        name=payload.threat_context.asset_name,
        criticality_score=9.8,
        hardware_replacement_cost_inr_cr=payload.threat_context.asset_replacement_cost_cr,
        daily_revenue_impact_inr_cr=payload.threat_context.daily_revenue_impact_cr,
        regulatory_tier=payload.threat_context.regulatory_tier,
        asset_type="infrastructure",
    )
    epss_out = EPSSOutput(
        cve_id=payload.epss_prediction.cve_id,
        z_score=-1.5,
        p_exploit=payload.epss_prediction.epss_probability,
        feature_contributions={"vend_microsoft": 2.44, "exp_weaponized": 2.00},
    )
    fair_out = FAIROutput(
        asset_id="AST-001",
        cve_id=payload.epss_prediction.cve_id,
        lef=payload.epss_prediction.epss_probability * 0.35,
        primary_loss_inr_cr=payload.fair_result.primary_loss_cr,
        secondary_loss_inr_cr=payload.fair_result.secondary_loss_cr,
        eal_inr_cr=payload.fair_result.expected_annual_loss_cr,
        var_95_inr_cr=payload.fair_result.value_at_risk_95_cr,
        trial_samples=[],
    )
    xai_out = XAIOutput(
        trust_score_pct=payload.xai_trust.trust_score_pct,
        iqr_threshold=0.85,
        flags_status=payload.xai_trust.alignment_status,
        misaligned_tokens=[],
    )
    milprosi_out = MILPROSIOutput(
        control_cost_inr_cr=payload.rosi_result.control_cost_cr,
        risk_reduced_inr_cr=payload.rosi_result.risk_reduced_cr,
        net_capital_saved_inr_cr=payload.rosi_result.net_benefit_cr,
        rosi_pct=payload.rosi_result.rosi_percentage,
        is_economically_viable=payload.rosi_result.is_economically_viable,
        gordon_loeb_ceiling_inr_cr=payload.rosi_result.gordon_loeb_cap_cr,
    )
    slots_res = SlotExtractionResult(
        asset_target=payload.threat_context.asset_name,
        cve_id=payload.epss_prediction.cve_id,
        budget_limit=payload.threat_context.proposed_control_cost_lakhs,
        timeline_delta=30,
        confidence=0.95,
    )

    return DeterministicContextPayload(
        session_id=session_id,
        persona=persona,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        slots=slots_res,
        asset=asset_node,
        epss=epss_out,
        fair=fair_out,
        xai=xai_out,
        milprosi=milprosi_out,
        compliance_controls=[],
        guardrail_passed=True,
        guardrail_errors=[],
    )


@router.post("/chat/business", response_model=ChatResponse)
async def chat_business(request: ChatRequest) -> ChatResponse:
    """Run core engines, format executive business briefing, verify financial integrity, return ChatResponse."""
    start_time = time.perf_counter()
    prompt = request.prompt or ""

    # Execute core engines
    execution_payload = _run_core_engines(prompt, request.context_overrides)

    # Synthesize plain-English executive briefing
    formatted_output = format_business_briefing(execution_payload)

    # Sanity guardrail verification
    passed, errors = guardrail.verify_financial_integrity(execution_payload, formatted_output)

    context_payload = _build_context_payload(execution_payload, request.session_id, PersonaType.BUSINESS)
    context_payload.guardrail_passed = passed
    context_payload.guardrail_errors = errors

    latency_ms = (time.perf_counter() - start_time) * 1000.0

    return ChatResponse(
        session_id=request.session_id,
        persona=PersonaType.BUSINESS,
        formatted_output=formatted_output,
        context_payload=context_payload,
        latency_ms=round(latency_ms, 2),
    )


@router.post("/chat/technical", response_model=ChatResponse)
async def chat_technical(request: ChatRequest) -> ChatResponse:
    """Run core engines, format technical diagnostic, verify financial integrity, return ChatResponse."""
    start_time = time.perf_counter()
    prompt = request.prompt or ""

    # Execute core engines
    execution_payload = _run_core_engines(prompt, request.context_overrides)

    # Synthesize technical diagnostic
    formatted_output = format_technical_diagnostic(execution_payload)

    # Sanity guardrail verification
    passed, errors = guardrail.verify_financial_integrity(execution_payload, formatted_output)

    context_payload = _build_context_payload(execution_payload, request.session_id, PersonaType.TECHNICAL)
    context_payload.guardrail_passed = passed
    context_payload.guardrail_errors = errors

    latency_ms = (time.perf_counter() - start_time) * 1000.0

    return ChatResponse(
        session_id=request.session_id,
        persona=PersonaType.TECHNICAL,
        formatted_output=formatted_output,
        context_payload=context_payload,
        latency_ms=round(latency_ms, 2),
    )


@router.post("/models/stream-update")
async def stream_update(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Ingest live telemetry batch to update exploit weights via EPSSPredictor.continuous_online_update()."""
    telemetry_batch = payload.get("telemetry_batch") or payload.get("batch") or []
    if isinstance(payload, list):
        telemetry_batch = payload

    epss_predictor.continuous_online_update(telemetry_batch)
    return {
        "status": "success",
        "samples_ingested": len(telemetry_batch),
        "model_fitted": epss_predictor._sgd_fitted,
    }
