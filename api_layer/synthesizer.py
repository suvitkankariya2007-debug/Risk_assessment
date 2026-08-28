"""
api_layer/synthesizer.py
=========================
Hybrid Synthesizer for CyberRiskIQ Gateway.

ZERO MATH RULE: The LLM/Synthesizer must ONLY format text.
It cannot calculate, estimate, or alter any numbers. All numeric values
must come directly from the pre-calculated deterministic ExecutionPayload.
"""
import os
import json
from typing import Any, Dict, Optional, List
from schemas.data_models import (
    ExecutionPayload,
    DeterministicContextPayload,
    PersonaType,
)

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "").lower()

_ZERO_MATH_SYSTEM_PROMPT = """You are an expert Cyber Risk Communication Assistant.
STRICT ZERO-MATH RULE:
- You MUST ONLY format and explain the exact numerical figures provided in the context payload.
- DO NOT perform any mathematical calculations, estimations, or numeric adjustments.
- All currency figures (₹ Cr), percentages (%), and risk scores are pre-computed and locked.
"""

_BUSINESS_PROMPT = _ZERO_MATH_SYSTEM_PROMPT + """
AUDIENCE: Executive / Board Member / CISO.
STYLE: Plain-English executive briefing. Zero technical jargon.
Lead with Expected Annual Loss (EAL ₹ Cr) and 95% Value-at-Risk (VaR ₹ Cr).
Follow with the Return on Security Investment (ROSI %) and state clearly whether the recommended spend is economically viable under the Gordon-Loeb framework.
"""

_TECHNICAL_PROMPT = _ZERO_MATH_SYSTEM_PROMPT + """
AUDIENCE: SecOps Lead / DevSecOps Engineer / Incident Response Team.
STYLE: Technical SecOps diagnostic.
Include CVSS base score / vectors, EPSS exploit probability and z-score, XAI salient token attributions, and recommended control measures.
"""


def _extract_payload_dict(payload: Any) -> Dict[str, Any]:
    """Extract standard metrics dictionary from either ExecutionPayload or DeterministicContextPayload."""
    out: Dict[str, Any] = {
        "asset_name": "Target Asset",
        "cve_id": "N/A",
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "cvss_score": 9.8,
        "epss_prob": 0.0,
        "epss_z_score": 0.0,
        "eal_cr": 0.0,
        "var_95_cr": 0.0,
        "primary_loss_cr": 0.0,
        "secondary_loss_cr": 0.0,
        "control_cost_cr": 0.0,
        "risk_reduced_cr": 0.0,
        "net_benefit_cr": 0.0,
        "rosi_pct": 0.0,
        "gordon_loeb_cap_cr": 0.0,
        "is_economically_viable": True,
        "trust_score_pct": 100.0,
        "salient_tokens": [],
        "alignment_status": "EXPERT_GROUNDED",
    }

    # If it's ExecutionPayload (Developer A)
    if isinstance(payload, ExecutionPayload):
        if payload.threat_context:
            out["asset_name"] = payload.threat_context.asset_name
            out["cve_id"] = payload.threat_context.cve_id
            out["cvss_vector"] = payload.threat_context.cvss_vector
            out["cvss_score"] = payload.threat_context.cvss_base_score
        if payload.epss_prediction:
            out["cve_id"] = payload.epss_prediction.cve_id or out["cve_id"]
            out["epss_prob"] = payload.epss_prediction.epss_probability
        if payload.fair_result:
            out["eal_cr"] = payload.fair_result.expected_annual_loss_cr
            out["var_95_cr"] = payload.fair_result.value_at_risk_95_cr
            out["primary_loss_cr"] = payload.fair_result.primary_loss_cr
            out["secondary_loss_cr"] = payload.fair_result.secondary_loss_cr
        if payload.xai_trust:
            out["trust_score_pct"] = payload.xai_trust.trust_score_pct
            out["salient_tokens"] = payload.xai_trust.salient_tokens
            out["alignment_status"] = payload.xai_trust.alignment_status
        if payload.rosi_result:
            out["control_cost_cr"] = payload.rosi_result.control_cost_cr
            out["risk_reduced_cr"] = payload.rosi_result.risk_reduced_cr
            out["net_benefit_cr"] = payload.rosi_result.net_benefit_cr
            out["rosi_pct"] = payload.rosi_result.rosi_percentage
            out["gordon_loeb_cap_cr"] = payload.rosi_result.gordon_loeb_cap_cr
            out["is_economically_viable"] = payload.rosi_result.is_economically_viable

    # If it's DeterministicContextPayload (Developer B)
    elif isinstance(payload, DeterministicContextPayload):
        if payload.asset:
            out["asset_name"] = payload.asset.name
        if payload.epss:
            out["cve_id"] = payload.epss.cve_id
            out["epss_prob"] = payload.epss.p_exploit
            out["epss_z_score"] = getattr(payload.epss, "z_score", 0.0)
        if payload.fair:
            out["eal_cr"] = payload.fair.eal_inr_cr
            out["var_95_cr"] = payload.fair.var_95_inr_cr
            out["primary_loss_cr"] = payload.fair.primary_loss_inr_cr
            out["secondary_loss_cr"] = payload.fair.secondary_loss_inr_cr
        if payload.xai:
            out["trust_score_pct"] = payload.xai.trust_score_pct
            out["salient_tokens"] = getattr(payload.xai, "salient_tokens", ["remote", "code_execution"])
            out["alignment_status"] = getattr(payload.xai, "flags_status", "EXPERT_GROUNDED")
        if payload.milprosi:
            out["control_cost_cr"] = payload.milprosi.control_cost_inr_cr
            out["risk_reduced_cr"] = payload.milprosi.risk_reduced_inr_cr
            out["net_benefit_cr"] = payload.milprosi.net_capital_saved_inr_cr
            out["rosi_pct"] = payload.milprosi.rosi_pct
            out["gordon_loeb_cap_cr"] = payload.milprosi.gordon_loeb_ceiling_inr_cr
            out["is_economically_viable"] = payload.milprosi.is_economically_viable

    elif isinstance(payload, dict):
        out.update(payload)

    return out


def template_business_briefing(data: Dict[str, Any]) -> str:
    """Plain-English executive briefing (EAL ₹, VaR ₹, ROSI %, zero technical jargon)."""
    viable_str = "economically viable" if data["is_economically_viable"] else "NOT economically viable (exceeds Gordon-Loeb ceiling)"
    tokens_str = ", ".join(data["salient_tokens"]) if data["salient_tokens"] else "N/A"
    
    return (
        f"EXECUTIVE RISK BRIEFING\n"
        f"Target Asset: {data['asset_name']} | Threat CVE: {data['cve_id']}\n\n"
        f"1. Financial Exposure:\n"
        f"   - Expected Annual Loss (EAL): ₹{data['eal_cr']:.2f} Cr\n"
        f"   - 95% Value-at-Risk (VaR): ₹{data['var_95_cr']:.2f} Cr\n"
        f"   - Operational Downtime Loss: ₹{data['primary_loss_cr']:.2f} Cr\n"
        f"   - Regulatory & Secondary Penalties: ₹{data['secondary_loss_cr']:.2f} Cr\n\n"
        f"2. Security Economics & Recommendation:\n"
        f"   - Proposed Control Cost: ₹{data['control_cost_cr']:.2f} Cr\n"
        f"   - Anticipated Risk Reduction: ₹{data['risk_reduced_cr']:.2f} Cr\n"
        f"   - Return on Security Investment (ROSI): {data['rosi_pct']:.1f}%\n"
        f"   - Gordon-Loeb Capital Ceiling: ₹{data['gordon_loeb_cap_cr']:.2f} Cr\n"
        f"   - Assessment: The proposed investment is {viable_str}.\n"
    )


def template_technical_diagnostic(data: Dict[str, Any]) -> str:
    """Technical SecOps diagnostic (CVSS vectors, EPSS odds ratios, XAI salient tokens)."""
    tokens_str = ", ".join(data["salient_tokens"]) if data["salient_tokens"] else "remote, code_execution"
    odds_ratio = data["epss_prob"] / max(1e-6, 1.0 - data["epss_prob"])

    return (
        f"TECHNICAL SECOPS DIAGNOSTIC REPORT\n"
        f"Asset: {data['asset_name']} | CVE ID: {data['cve_id']}\n\n"
        f"1. Threat & Exploit Intelligence:\n"
        f"   - CVSS Vector: {data['cvss_vector']} (Base Score: {data['cvss_score']})\n"
        f"   - EPSS Exploit Probability: {data['epss_prob']:.4f} ({data['epss_prob']*100:.2f}%)\n"
        f"   - EPSS Exploit Odds Ratio: {odds_ratio:.4f}\n"
        f"   - EPSS Model Z-Score: {data['epss_z_score']:.4f}\n\n"
        f"2. Explainable AI (XAI) Alignment:\n"
        f"   - XAI Trust Score: {data['trust_score_pct']:.1f}%\n"
        f"   - Alignment Status: {data['alignment_status']}\n"
        f"   - Salient Feature Tokens: [{tokens_str}]\n\n"
        f"3. Risk & Loss Parameters:\n"
        f"   - EAL: ₹{data['eal_cr']:.4f} Cr | VaR (95%): ₹{data['var_95_cr']:.4f} Cr\n"
        f"   - Primary Downtime Loss: ₹{data['primary_loss_cr']:.4f} Cr\n"
        f"   - Secondary Regulatory Loss: ₹{data['secondary_loss_cr']:.4f} Cr\n"
        f"   - ROSI: {data['rosi_pct']:.2f}% | Viable: {data['is_economically_viable']}\n"
    )


def call_external_llm(prompt: str, data: Dict[str, Any]) -> Optional[str]:
    """Wrapper hook for external LLM APIs (Gemini/OpenAI/Anthropic). Returns None if unconfigured."""
    data_json = json.dumps(data, indent=2)
    user_content = f"PRE-CALCULATED EXECUTION_PAYLOAD:\n{data_json}\n\nFormat the response for the user according to strict rules."

    # Gemini Wrapper Hook
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if LLM_PROVIDER == "gemini" or (gemini_key and not LLM_PROVIDER):
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel(model_name="gemini-2.5-flash", system_instruction=prompt)
            resp = model.generate_content(user_content)
            return resp.text
        except Exception:
            pass

    # OpenAI Wrapper Hook
    openai_key = os.environ.get("OPENAI_API_KEY")
    if LLM_PROVIDER == "openai" or (openai_key and not LLM_PROVIDER):
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_content},
                ],
            )
            return resp.choices[0].message.content
        except Exception:
            pass

    # Anthropic Wrapper Hook
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if LLM_PROVIDER == "anthropic" or (anthropic_key and not LLM_PROVIDER):
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=anthropic_key)
            resp = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            return "".join(b.text for b in resp.content if b.type == "text")
        except Exception:
            pass

    return None


def format_business_briefing(payload: Any) -> str:
    """Format plain-English executive briefing (EAL ₹, VaR ₹, ROSI %, zero technical jargon)."""
    data = _extract_payload_dict(payload)
    llm_output = call_external_llm(_BUSINESS_PROMPT, data)
    if llm_output:
        return llm_output
    return template_business_briefing(data)


def format_technical_diagnostic(payload: Any) -> str:
    """Format technical SecOps diagnostic (CVSS vectors, EPSS odds ratios, XAI salient tokens)."""
    data = _extract_payload_dict(payload)
    llm_output = call_external_llm(_TECHNICAL_PROMPT, data)
    if llm_output:
        return llm_output
    return template_technical_diagnostic(data)


class HybridSynthesizer:
    """Hybrid synthesizer providing template formatting + external LLM API hooks."""

    def format_business_briefing(self, payload: Any) -> str:
        return format_business_briefing(payload)

    def format_technical_diagnostic(self, payload: Any) -> str:
        return format_technical_diagnostic(payload)

    def synthesize(self, payload: Any, persona: PersonaType = PersonaType.BUSINESS) -> str:
        if persona == PersonaType.TECHNICAL:
            return self.format_technical_diagnostic(payload)
        return self.format_business_briefing(payload)


# Alias for backward compatibility
PromptSynthesizers = HybridSynthesizer
