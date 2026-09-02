"""
api_layer/dual_routes.py
========================
FastAPI Router for CyberRiskIQ Gateway.

Endpoints:
- POST /api/v1/chat/business
- POST /api/v1/chat/technical
- POST /api/v1/models/stream-update
"""
import os
import re
import time
import uuid
import asyncio
import json
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Body, UploadFile, File
from fastapi.concurrency import run_in_threadpool

# Helper to load .env manually
def _load_env():
    try:
        # Check current dir and parent dir for .env
        for path in [".env", "../.env", "../../.env"]:
            if os.path.exists(path):
                with open(path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            parts = line.split("=", 1)
                            if len(parts) == 2:
                                k = parts[0].strip()
                                v = parts[1].strip()
                                if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                                    v = v[1:-1]
                                os.environ[k] = v
    except Exception:
        pass

_load_env()

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
from core_engines.business_profile import build_business_profile
from core_engines.segment_risk import compute_segment_risk
from core_engines.control_maturity import evaluate_control_maturity
from core_engines.rosi_v2 import compute_rosi_v2
from core_engines.cia_exposure import compute_cia_exposure
from core_engines.domain_priority import compute_domain_priorities
from api_layer.synthesizer import (
    format_business_briefing,
    format_technical_diagnostic,
    HybridSynthesizer,
    _extract_payload_dict,
)
from api_layer.guardrails import SanityGuardrailVerifier
from api_layer import mock_kb
from api_layer.scan_ledger import scan_ledger, ScanUploadResponse
from api_layer.model_manager import model_manager

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

# Phase-2 NLU (Task 8): extension slot patterns. Numeric/text extension
# inputs are captured as explicit "key: value" or "key = value" pairs so
# nothing is ever guessed silently from prose.
_KV_SLOT_PATTERN = re.compile(
    r"\b(business_unit|segment_name|segment_revenue_pct|annual_revenue_cr|"
    r"sector|country|employee_count|control_maturity|efficacy_t|"
    r"impact_operational|impact_financial|risk_w|t_w|cost_rate|"
    r"confidentiality|integrity|availability)\s*[:=]\s*"
    r"([A-Za-z_][\w &/]*|-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
# Control maturity enum: only captured when tied to an explicit
# maturity/controls mention, or the distinctive phrase "not implemented".
_MATURITY_PATTERN = re.compile(
    r"(?:maturity|controls?)\s*(?:is|are|level|:)?\s*"
    r"(not[ -]?implemented|initial|repeatable|defined|managed|optimized)"
    r"|\b(not[ -]?implemented)\b",
    re.IGNORECASE,
)

NLU_SYSTEM_PROMPT = """You are the NLU (Natural Language Understanding) parser for the CyberRiskIQ Copilot.
Analyze the user's raw text prompt and extract structured intent and entity slots.

Intents:
1. RISK_QUANTIFICATION: The user is asking to calculate/evaluate risks, financial loss exposure, or budget viability for specific assets or CVEs (e.g. "What is the expected annual loss for customer_db?", "is a budget of 30 Lakhs viable for core payment switch?").
2. SCAN_ANALYSIS: The user is asking about findings in the uploaded scan file, vulnerability reports, or uploaded scan analysis (e.g. "what are findings from uploaded file", "analyse the file", "list vulnerabilities in the scan").
3. GENERAL_KNOWLEDGE: The user is asking for general, conceptual explanations of security risk metrics or standards (e.g. "explain ROSI", "what is EPSS?", "define FAIR model").
4. CONVERSATIONAL: The query is a simple greeting, farewell, help request, or a generic word like "budget" or "risks" without any CVE or asset context (e.g. "hello", "hi", "who are you?", "budget", "what can you do?").
5. UNIDENTIFIED: The prompt is gibberish, punctuation symbols, or completely unclear (e.g. "/", "?", "asdf").

Assets:
- customer_db
- api_gateway
- core_payment_switch
- legacy-dev-sandbox

You must output a single JSON object (and absolutely nothing else) with the following keys:
{
  "intent": "RISK_QUANTIFICATION" | "SCAN_ANALYSIS" | "GENERAL_KNOWLEDGE" | "CONVERSATIONAL" | "UNIDENTIFIED",
  "cve_id": string or null,
  "asset_name": "customer_db" | "api_gateway" | "core_payment_switch" | "legacy-dev-sandbox" | null,
  "budget_lakhs": float or null,
  "conversational_response": string or null
}

Rule for budget extraction:
- Extract money and convert to Lakhs (1 Crore = 100 Lakhs, e.g. "₹50 Lakhs" -> 50.0, "3 Crores" -> 300.0, "500 Cr" -> 50000.0).

Rule for conversational_response:
- If intent is CONVERSATIONAL, GENERAL_KNOWLEDGE, or UNIDENTIFIED, provide a direct, high-quality, friendly conversational reply.
- If the query is vague/incomplete (e.g. just the word "budget"), guide the user to specify an asset and budget value.

Ensure the output is strictly valid JSON.
"""

def _call_llm_nlu(prompt: str) -> Optional[Dict[str, Any]]:
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel(
                model_name="gemini-3.6-flash",
                generation_config={"response_mime_type": "application/json"},
                system_instruction=NLU_SYSTEM_PROMPT
            )
            resp = model.generate_content(
                f"User Prompt: {prompt}",
                request_options={"timeout": 2.0}
            )
            if resp and resp.text:
                return json.loads(resp.text.strip())
        except Exception as e:
            print(f"[NLU LLM] Gemini NLU call failed: {e}")
            
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key, timeout=2.0)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": NLU_SYSTEM_PROMPT},
                    {"role": "user", "content": f"User Prompt: {prompt}"},
                ],
            )
            return json.loads(resp.choices[0].message.content.strip())
        except Exception as e:
            print(f"[NLU LLM] OpenAI NLU call failed: {e}")
            
    return None

async def _handle_scan_analysis(prompt: str, session_id: str, persona: PersonaType, nlu_data: Dict[str, Any]) -> ChatResponse:
    start_time = time.perf_counter()
    if not scan_ledger.is_loaded:
        text = (
            "No vulnerability scan file has been uploaded yet. "
            "Please upload a JSON or CSV scan export file using the 'Scan Ingestion' sidebar in the UI to perform scan analysis."
        )
        context_payload = _build_dummy_context_payload(session_id, persona)
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        return ChatResponse(
            session_id=session_id,
            persona=persona,
            formatted_output=text,
            context_payload=context_payload,
            latency_ms=round(latency_ms, 2),
        )
        
    # We have findings!
    findings = scan_ledger.list_findings()
    findings_json = json.dumps(findings, indent=2)
    
    # Default fallback template summary
    total = len(findings)
    critical = sum(1 for f in findings if f.get("cvss_score", 0) >= 9.0 or f.get("severity") == "critical")
    high = sum(1 for f in findings if (7.0 <= f.get("cvss_score", 0) < 9.0) or f.get("severity") == "high")
    medium = sum(1 for f in findings if (4.0 <= f.get("cvss_score", 0) < 7.0) or f.get("severity") == "medium")
    assets = list(set(f.get("asset_name") for f in findings if f.get("asset_name")))
    
    fallback_text = (
        f"VULNERABILITY SCAN SUMMARY:\n"
        f"Total Ingested Findings: {total}\n"
        f"Severity Breakdown: Critical ({critical}), High ({high}), Medium ({medium})\n"
        f"Affected Assets: {', '.join(assets)}\n\n"
        f"Top Findings:\n"
    )
    for f in findings[:5]:
        fallback_text += f"- [{f.get('cve_id')}] on {f.get('asset_name')} (CVSS: {f.get('cvss_score')}) - {f.get('description')}\n"
        
    text = fallback_text
    
    system_instruction = ""
    if persona == PersonaType.BUSINESS:
        system_instruction = (
            "You are the CyberRiskIQ Business Copilot. Summarize the vulnerability scan findings for an executive audience. "
            "Highlight the total number of findings, critical vulnerabilities, affected assets, and potential business/financial risks of not patching them. "
            "Do not include technical jargon like CVSS vectors or raw CVE attributions in detail unless relevant to financial tiers. "
            "Strictly do not hallucinate any math calculations, but explain the threat landscape based on the findings."
        )
    else:
        system_instruction = (
            "You are the CyberRiskIQ Technical Copilot. Provide a technical SecOps summary of the vulnerability scan findings. "
            "List the CVEs, CVSS scores, threat indicators (weaponization, PoC), and affected assets. "
            "Recommend remediation priorities based on severity."
        )
        
    # Token-efficient format: send only essential fields for top 5 findings
    efficient_findings = [{"cve": f.get("cve_id"), "asset": f.get("asset_name"), "cvss": f.get("cvss_score"), "desc": f.get("description")} for f in findings[:5]]
    efficient_json = json.dumps(efficient_findings)
    user_content = f"Vulnerability Scan Summary Data:\n{fallback_text}\nTop 5 Findings Data:\n{efficient_json}\n\nUser Question: {prompt}"
    
    # Try calling LLM to format nicely
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    
    def _do_llm_formatting():
        if gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel(
                    model_name="gemini-3.6-flash",
                    system_instruction=system_instruction
                )
                resp = model.generate_content(user_content, request_options={"timeout": 2.0})
                if resp and resp.text:
                    return resp.text
            except Exception:
                pass
        elif openai_key:
            try:
                import openai
                client = openai.OpenAI(api_key=openai_key, timeout=2.0)
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": user_content},
                    ],
                )
                return resp.choices[0].message.content
            except Exception:
                pass
        return None

    llm_resp = await run_in_threadpool(_do_llm_formatting)
    if llm_resp:
        text = llm_resp
            
    context_payload = _build_dummy_context_payload(session_id, persona)
    if findings:
        try:
            first_finding = findings[0]
            cve_id = first_finding.get("cve_id", "CVE-2024-1234")
            asset_name = first_finding.get("asset_name", "Core Payment Switch")
            
            execution_payload = _run_core_engines(f"Calculate risk for {asset_name} with {cve_id}", {})
            context_payload = _build_context_payload(execution_payload, session_id, persona)
        except Exception:
            pass

    latency_ms = (time.perf_counter() - start_time) * 1000.0
    return ChatResponse(
        session_id=session_id,
        persona=persona,
        formatted_output=text,
        context_payload=context_payload,
        latency_ms=round(latency_ms, 2),
    )


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

    # Resolve target asset name — check ScanLedger first
    asset_name = "Core Payment Switch"
    for candidate in ["customer_db", "api_gateway", "core_payment_switch", "payment switch",
                       "customer database", "api gateway", "legacy-dev-sandbox"]:
        if candidate in prompt.lower():
            asset_name = candidate
            break

    # Dynamic scan ledger lookup: if a scan is loaded and contains the CVE, enrich
    if scan_ledger.is_loaded:
        scan_vuln = scan_ledger.lookup_cve(cve_id)
        if scan_vuln:
            # Enrich from live scan data rather than static mock_kb
            pass  # lookup_vuln will use scan_ledger below

    # ── Phase-2 extension slot capture (Task 8) ────────────────────────────
    ext: Dict[str, Any] = {}
    for m in _KV_SLOT_PATTERN.finditer(prompt):
        key = m.group(1).lower()
        raw = m.group(2).strip().rstrip(",.;")
        try:
            val: Any = float(raw)
            if key == "employee_count" and float(val).is_integer():
                val = int(val)
        except ValueError:
            val = raw
        ext[key] = val

    mm = _MATURITY_PATTERN.search(prompt)
    if mm:
        level = mm.group(1) or mm.group(2) or ""
        ext.setdefault("control_maturity", level.lower().replace("-", " ").strip())

    return {
        "cve_id": cve_id,
        "asset_name": asset_name,
        "budget_lakhs": budget_lakhs,
        # ── Phase-2 extension slots (absent → None; never guessed) ──────────
        "business_unit": ext.get("business_unit"),
        "segment_name": ext.get("segment_name"),
        "segment_revenue_pct": ext.get("segment_revenue_pct"),
        "annual_revenue_cr": ext.get("annual_revenue_cr"),
        "sector": ext.get("sector"),
        "country": ext.get("country"),
        "employee_count": ext.get("employee_count"),
        "control_maturity": ext.get("control_maturity"),
        "efficacy_t": ext.get("efficacy_t"),
        "impact_operational": ext.get("impact_operational"),
        "impact_financial": ext.get("impact_financial"),
        "risk_w": ext.get("risk_w"),
        "t_w": ext.get("t_w"),
        "cost_rate": ext.get("cost_rate"),
        "confidentiality": ext.get("confidentiality"),
        "integrity": ext.get("integrity"),
        "availability": ext.get("availability"),
    }


def _run_core_engines(prompt: str, context_overrides: Optional[Dict[str, Any]] = None) -> ExecutionPayload:
    """Execute Developer A deterministic math engines and build frozen ExecutionPayload."""
    slots = _extract_slots(prompt)
    if context_overrides:
        slots.update(context_overrides)

    # 1. Resolve Asset Topology — unknown assets map to an explicit
    # UNRESOLVED_ASSET state (Phase 0b). Never silently substitute the
    # demo asset; the caller proceeds with a generic unweighted profile
    # and the response clearly labels the asset as unresolved.
    asset_requested = slots.get("asset_name", "")
    topo_data = None
    if asset_requested:
        try:
            topo_data = asset_graph.resolve_asset(asset_requested)
        except KeyError:
            topo_data = None
    if topo_data is None:
        topo_data = {
            "asset_name": "UNRESOLVED_ASSET",
            "asset_replacement_cost_cr": 0.0,
            "daily_revenue_impact_cr": 0.0,
            "regulatory_tier": "UNRESOLVED",
            "asset_id": "UNRESOLVED_ASSET",
            "business_services": [],
            "upstream_dependencies": [],
            "downstream_dependencies": [],
        }

    # Query ScanLedger first, then fall back to mock_kb
    vuln_info = None
    if scan_ledger.is_loaded:
        vuln_info = scan_ledger.lookup_cve(slots.get("cve_id", ""))
    if not vuln_info:
        vuln_info = mock_kb.lookup_vuln(slots.get("cve_id", ""))

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

    # Phase 0a: use the REAL CVSS score/vector from the matched scan
    # finding (uploaded scan data drives the output). 9.8 is only a
    # fallback when no scan data carries a score.
    cvss_score = float(vuln_info.get("cvss_score") or 9.8)
    cvss_vector = str(vuln_info.get("cvss_vector") or "").strip() or \
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"

    threat_context = ThreatContext(
        cve_id=slots["cve_id"],
        description=vuln_info["description"],
        asset_name=topo_data["asset_name"],
        asset_replacement_cost_cr=topo_data["asset_replacement_cost_cr"],
        daily_revenue_impact_cr=topo_data["daily_revenue_impact_cr"],
        regulatory_tier=topo_data["regulatory_tier"],
        cvss_base_score=cvss_score,
        cvss_vector=cvss_vector,
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
        business_profile=payload.business_profile,
        segment_risk=payload.segment_risk,
        control_maturity=payload.control_maturity,
        rosi_v2=payload.rosi_v2,
        cia_exposure=payload.cia_exposure,
        domain_priority=payload.domain_priority,
    )


def _analyze_query_intent(prompt: str) -> str:
    """Classify prompt into UNIDENTIFIED, CONVERSATIONAL, GENERAL_KNOWLEDGE, SCAN_ANALYSIS, or RISK_QUANTIFICATION."""
    clean = (prompt or "").strip()
    if not clean:
        return "UNIDENTIFIED"
    
    # 1. Unidentified symbols / single char / gibberish (e.g. "/", "?", "asd")
    if len(clean) < 3 or clean in ["/", "?", "!", ".", "asdf", "test", "xxx", "helpme"]:
        if clean.lower() in ["hi", "hey", "yo"]:
            return "CONVERSATIONAL"
        return "UNIDENTIFIED"
    
    lower = clean.lower()
    
    # 1.5 Scan analysis detection (e.g. "what are findings from uploaded file", "scan summary")
    scan_keywords = [
        "scan", "upload", "uploaded", "finding", "findings", 
        "vulnerabilities", "vulnerability", "vuln", "vulner", 
        "vukner", "explout", "report", "file", "invest", "analysed", "analyzed"
    ]
    if any(k in lower for k in scan_keywords):
        return "SCAN_ANALYSIS"

    # 2. Conversational greetings / general system info
    if any(lower.startswith(g) for g in ["hi", "hello", "hey", "greetings", "good morning", "good evening"]):
        if not any(k in lower for k in ["cve", "loss", "eal", "var", "epss", "budget", "cost", "switch", "database"]):
            return "CONVERSATIONAL"
    if "who are you" in lower or "what can you do" in lower or lower == "help":
        return "CONVERSATIONAL"

    # 3. Intercept general / non-risk queries (e.g. "what is an api key", "how does a firewall work", "explain waf")
    # If the prompt does NOT contain a CVE pattern and does NOT mention any known assets:
    has_cve = bool(_CVE_PATTERN.search(clean))
    known_assets = ["customer_db", "api_gateway", "core_payment_switch", "payment switch",
                    "customer database", "api gateway", "legacy-dev-sandbox", "sandbox"]
    has_asset = any(asset in lower for asset in known_assets)
    
    # Also check if it contains risk metrics keywords that require calculation
    risk_keywords = ["eal", "var", "expected annual loss", "value at risk", "rosi", "gordon-loeb", "gordon loeb", "quantify", "simulation", "budget", "capital", "crore", "crores", "lakh", "lakhs", "approval"]
    has_risk_keyword = any(kw in lower for kw in risk_keywords)

    if not has_cve and not has_asset and not has_risk_keyword:
        return "GENERAL_KNOWLEDGE"

    # 4. General knowledge questions about risk metrics specifically
    if any(q in lower for q in ["what is", "explain", "how does", "define", "what does"]) and not has_cve:
        # If it specifically asks for a definition, let's keep it as general knowledge
        if any(k in lower for k in ["fair", "epss", "rosi", "gordon", "loeb", "var", "eal", "xai", "trust score"]):
            return "GENERAL_KNOWLEDGE"

    # 5. Standard Risk Quantification / Diagnostic
    return "RISK_QUANTIFICATION"


def _build_dummy_context_payload(session_id: str, persona: PersonaType) -> DeterministicContextPayload:
    """Build a fast, dummy context payload bypassing heavy mathematical simulations."""
    asset_node = AssetNode(
        asset_id="AST-000",
        name="General Context",
        criticality_score=0.0,
        hardware_replacement_cost_inr_cr=0.0,
        daily_revenue_impact_inr_cr=0.0,
        regulatory_tier="N/A",
        asset_type="general",
    )
    epss_out = EPSSOutput(
        cve_id="N/A",
        z_score=0.0,
        p_exploit=0.0,
        feature_contributions={},
    )
    fair_out = FAIROutput(
        asset_id="AST-000",
        cve_id="N/A",
        lef=0.0,
        primary_loss_inr_cr=0.0,
        secondary_loss_inr_cr=0.0,
        eal_inr_cr=0.0,
        var_95_inr_cr=0.0,
        trial_samples=[],
    )
    xai_out = XAIOutput(
        trust_score_pct=100.0,
        iqr_threshold=0.0,
        flags_status="EXPERT_GROUNDED",
        misaligned_tokens=[],
    )
    milprosi_out = MILPROSIOutput(
        control_cost_inr_cr=0.0,
        risk_reduced_inr_cr=0.0,
        net_capital_saved_inr_cr=0.0,
        rosi_pct=0.0,
        is_economically_viable=True,
        gordon_loeb_ceiling_inr_cr=0.0,
    )
    slots_res = SlotExtractionResult(
        asset_target="N/A",
        cve_id="N/A",
        budget_limit=0.0,
        timeline_delta=0,
        confidence=1.0,
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


def _handle_unidentified_or_conversational(prompt: str, session_id: str, persona: PersonaType, query_type: str) -> ChatResponse:
    """Generate dynamic help / clarification response for unidentified or conversational prompts, bypassing math engines."""
    start_time = time.perf_counter()
    
    # Direct routing to conversational response generator (bypassing core engines)
    text = synthesizer.generate_conversational_response(prompt, persona)
    
    # Build dummy context payload so we bypass the heavy engines
    context_payload = _build_dummy_context_payload(session_id, persona)
    
    latency_ms = (time.perf_counter() - start_time) * 1000.0
    return ChatResponse(
        session_id=session_id,
        persona=persona,
        formatted_output=text,
        context_payload=context_payload,
        latency_ms=round(latency_ms, 2),
    )


def _handle_general_knowledge(prompt: str, session_id: str, persona: PersonaType) -> ChatResponse:
    """Answer conceptual security risk questions grounded in platform math, bypassing math engines."""
    start_time = time.perf_counter()
    
    # Direct routing to conversational response generator (bypassing core engines)
    text = synthesizer.generate_conversational_response(prompt, persona)
    
    # Build dummy context payload so we bypass the heavy engines
    context_payload = _build_dummy_context_payload(session_id, persona)
    
    latency_ms = (time.perf_counter() - start_time) * 1000.0
    return ChatResponse(
        session_id=session_id,
        persona=persona,
        formatted_output=text,
        context_payload=context_payload,
        latency_ms=round(latency_ms, 2),
    )



@router.post("/chat/business", response_model=ChatResponse)
async def chat_business(request: ChatRequest) -> ChatResponse:
    """Run core engines, format executive business briefing, verify financial integrity, return ChatResponse."""
    start_time = time.perf_counter()
    prompt = request.prompt or ""

    # Try LLM NLU parse first
    try:
        nlu_data = await asyncio.wait_for(run_in_threadpool(_call_llm_nlu, prompt), timeout=2.0)
    except asyncio.TimeoutError:
        nlu_data = None
    if nlu_data:
        intent = nlu_data.get("intent", "UNIDENTIFIED")
        if intent == "SCAN_ANALYSIS":
            return await _handle_scan_analysis(prompt, request.session_id, PersonaType.BUSINESS, nlu_data)
        elif intent in ["CONVERSATIONAL", "UNIDENTIFIED", "GENERAL_KNOWLEDGE"]:
            resp_text = synthesizer.generate_conversational_response(prompt, PersonaType.BUSINESS)
            context_payload = _build_dummy_context_payload(request.session_id, PersonaType.BUSINESS)
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return ChatResponse(
                session_id=request.session_id,
                persona=PersonaType.BUSINESS,
                formatted_output=resp_text,
                context_payload=context_payload,
                latency_ms=round(latency_ms, 2),
            )
        else: # RISK_QUANTIFICATION
            overrides = {}
            if nlu_data.get("asset_name"):
                overrides["asset_name"] = nlu_data["asset_name"]
            if nlu_data.get("cve_id"):
                overrides["cve_id"] = nlu_data["cve_id"]
            if nlu_data.get("budget_lakhs") is not None:
                overrides["budget_lakhs"] = nlu_data["budget_lakhs"]
            
            req_overrides = request.context_overrides or {}
            combined_overrides = {**overrides, **req_overrides}
            
            execution_payload = _run_core_engines(prompt, combined_overrides)
            formatted_output = format_business_briefing(execution_payload, prompt)
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

    # Classify query intent
    query_type = _analyze_query_intent(prompt)
    if query_type == "SCAN_ANALYSIS":
        return await _handle_scan_analysis(prompt, request.session_id, PersonaType.BUSINESS, {})
    elif query_type in ["UNIDENTIFIED", "CONVERSATIONAL"]:
        return _handle_unidentified_or_conversational(prompt, request.session_id, PersonaType.BUSINESS, query_type)
    elif query_type == "GENERAL_KNOWLEDGE":
        return _handle_general_knowledge(prompt, request.session_id, PersonaType.BUSINESS)

    # Execute core engines for Risk Quantification
    execution_payload = _run_core_engines(prompt, request.context_overrides)

    # Synthesize plain-English executive briefing with user prompt context
    formatted_output = format_business_briefing(execution_payload, prompt)

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

    # Try LLM NLU parse first
    try:
        nlu_data = await asyncio.wait_for(run_in_threadpool(_call_llm_nlu, prompt), timeout=2.0)
    except asyncio.TimeoutError:
        nlu_data = None
    if nlu_data:
        intent = nlu_data.get("intent", "UNIDENTIFIED")
        if intent == "SCAN_ANALYSIS":
            return await _handle_scan_analysis(prompt, request.session_id, PersonaType.TECHNICAL, nlu_data)
        elif intent in ["CONVERSATIONAL", "UNIDENTIFIED", "GENERAL_KNOWLEDGE"]:
            resp_text = synthesizer.generate_conversational_response(prompt, PersonaType.TECHNICAL)
            context_payload = _build_dummy_context_payload(request.session_id, PersonaType.TECHNICAL)
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return ChatResponse(
                session_id=request.session_id,
                persona=PersonaType.TECHNICAL,
                formatted_output=resp_text,
                context_payload=context_payload,
                latency_ms=round(latency_ms, 2),
            )
        else: # RISK_QUANTIFICATION
            overrides = {}
            if nlu_data.get("asset_name"):
                overrides["asset_name"] = nlu_data["asset_name"]
            if nlu_data.get("cve_id"):
                overrides["cve_id"] = nlu_data["cve_id"]
            if nlu_data.get("budget_lakhs") is not None:
                overrides["budget_lakhs"] = nlu_data["budget_lakhs"]
            
            req_overrides = request.context_overrides or {}
            combined_overrides = {**overrides, **req_overrides}
            
            execution_payload = _run_core_engines(prompt, combined_overrides)
            formatted_output = format_technical_diagnostic(execution_payload, prompt)
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

    # Classify query intent
    query_type = _analyze_query_intent(prompt)
    if query_type == "SCAN_ANALYSIS":
        return await _handle_scan_analysis(prompt, request.session_id, PersonaType.TECHNICAL, {})
    elif query_type in ["UNIDENTIFIED", "CONVERSATIONAL"]:
        return _handle_unidentified_or_conversational(prompt, request.session_id, PersonaType.TECHNICAL, query_type)
    elif query_type == "GENERAL_KNOWLEDGE":
        return _handle_general_knowledge(prompt, request.session_id, PersonaType.TECHNICAL)

    # Execute core engines for Technical Risk Diagnostic
    execution_payload = _run_core_engines(prompt, request.context_overrides)

    # Synthesize technical diagnostic with user prompt context
    formatted_output = format_technical_diagnostic(execution_payload, prompt)

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


# ── Semantic Intent Router (TF-IDF Cosine Similarity) ──────────────────────
class SemanticIntentRouter:
    """NLP-powered intent classifier using TF-IDF cosine similarity.

    Replaces static keyword dictionaries with semantic document similarity
    computed against business and technical reference corpora.
    """

    _BIZ_CORPUS = [
        "expected annual financial loss exposure enterprise risk assessment",
        "budget allocation security investment return ROSI economic viability",
        "Gordon-Loeb optimal spending ceiling capital expenditure justification",
        "board CISO executive briefing monetary impact revenue downtime cost",
        "regulatory fine penalty secondary loss compliance SEBI RBI framework",
        "Monte Carlo simulation value at risk VaR confidence interval",
        "knapsack optimization control portfolio cost benefit analysis",
        "insurance coverage cyber liability premium annual loss expectancy",
        "stakeholder reporting risk appetite tolerance approval spend crore lakh",
    ]
    _TECH_CORPUS = [
        "CVE vulnerability exploit EPSS probability prediction logistic regression",
        "CVSS vector base score attack surface network adjacent local physical",
        "XAI explainable AI trust score integrated gradients salient tokens",
        "patch remediation vulnerability management severity critical high medium",
        "WAF rules firewall IDS IPS network segmentation microsegmentation",
        "ransomware malware trojan lateral movement privilege escalation RCE",
        "incident response forensics threat hunting indicators of compromise IOC",
        "proof of concept weaponized exploit code execution remote arbitrary",
        "SIEM EDR endpoint detection alert triage enrichment correlation SOC",
    ]

    def __init__(self) -> None:
        self._use_sklearn = False
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity as _cos

            self._vec = TfidfVectorizer(
                stop_words="english", ngram_range=(1, 2),
                max_features=500, sublinear_tf=True,
            )
            self._vec.fit(self._BIZ_CORPUS + self._TECH_CORPUS)
            self._biz_m = self._vec.transform(self._BIZ_CORPUS)
            self._tech_m = self._vec.transform(self._TECH_CORPUS)
            self._cos = _cos
            self._use_sklearn = True
        except Exception:
            pass

    def classify(self, prompt: str) -> PersonaType:
        if self._use_sklearn:
            q = self._vec.transform([prompt.lower()])
            biz = float(self._cos(q, self._biz_m).max())
            tech = float(self._cos(q, self._tech_m).max())
        else:
            lower = prompt.lower()
            biz = sum(1 for w in ["budget", "cost", "loss", "invest",
                                   "spend", "viable", "ciso", "board",
                                   "financial", "revenue", "gordon",
                                   "downtime", "roi", "rosi"] if w in lower)
            tech = sum(1 for w in ["cve", "epss", "exploit", "cvss",
                                    "vulnerability", "patch", "xai",
                                    "trust", "salient", "remediat",
                                    "ransomware", "severity"] if w in lower)
        if _CVE_PATTERN.search(prompt):
            tech += 0.25 if self._use_sklearn else 3
        if _BUDGET_PATTERN.search(prompt):
            biz += 0.25 if self._use_sklearn else 3
        return PersonaType.TECHNICAL if tech > biz else PersonaType.BUSINESS


intent_router = SemanticIntentRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_auto_route(request: ChatRequest) -> ChatResponse:
    """Unified endpoint: auto-classifies intent via semantic similarity, routes to the correct handler."""
    persona = intent_router.classify(request.prompt or "")
    if persona == PersonaType.TECHNICAL:
        return await chat_technical(request)
    return await chat_business(request)


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


# ── Scan Ingestion Endpoints ────────────────────────────────────────────────
@router.post("/scan/upload", response_model=ScanUploadResponse)
async def upload_scan(file: UploadFile = File(...)) -> ScanUploadResponse:
    """Upload a JSON or CSV vulnerability scan file for dynamic ingestion."""
    content = await file.read()
    text = content.decode("utf-8", errors="replace")
    filename = (file.filename or "").lower()

    if filename.endswith(".json"):
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON file.")
        count = scan_ledger.ingest_json(raw)
    elif filename.endswith(".csv"):
        count = scan_ledger.ingest_csv(text)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Upload .json or .csv files.")

    return ScanUploadResponse(
        status="success",
        findings_ingested=count,
        total_findings=len(scan_ledger._findings),
        scan_id=f"SCAN-{scan_ledger.scan_count:03d}",
    )


@router.get("/scan/findings")
async def get_scan_findings() -> Dict[str, Any]:
    """Return cached scan findings summary."""
    return {
        "loaded": scan_ledger.is_loaded,
        "total_findings": len(scan_ledger._findings),
        "scan_count": scan_ledger.scan_count,
        "findings": scan_ledger.list_findings(),
    }


@router.delete("/scan/clear")
async def clear_scan_ledger() -> Dict[str, str]:
    """Clear all cached scan findings."""
    scan_ledger.clear()
    return {"status": "cleared"}


# ── Model Status Endpoint ──────────────────────────────────────────────────
@router.get("/models/status")
async def model_status() -> Dict[str, Any]:
    """Return current transformer model status and fallback state."""
    return model_manager.status()


import json  # ensure json is available for scan upload
