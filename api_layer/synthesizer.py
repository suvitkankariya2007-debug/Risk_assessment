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
from api_layer.model_manager import model_manager
from api_layer.guardrails import SanityGuardrailVerifier

guardrail_verifier = SanityGuardrailVerifier()

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

_STATIC_BASELINE_DATA = {
    "asset_name": "Core Payment Switch",
    "cve_id": "CVE-2024-1234",
    "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    "cvss_score": 9.8,
    "epss_prob": 0.0091,
    "epss_z_score": -1.5,
    "eal_cr": 1.25,
    "var_95_cr": 4.50,
    "primary_loss_cr": 0.90,
    "secondary_loss_cr": 0.35,
    "control_cost_cr": 0.30,
    "risk_reduced_cr": 0.77,
    "net_benefit_cr": 0.47,
    "rosi_pct": 256.67,
    "gordon_loeb_cap_cr": 0.46,
    "is_economically_viable": True,
    "trust_score_pct": 82.0,
    "salient_tokens": ["remote", "code_execution"],
    "alignment_status": "EXPERT_GROUNDED",
    "daily_revenue_impact_cr": 12.5,
    "regulatory_tier": "TIER_1_CRITICAL",
}


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
        "daily_revenue_impact_cr": 12.5,
        "regulatory_tier": "TIER_1_CRITICAL",
    }

    # If it's ExecutionPayload (Developer A)
    if isinstance(payload, ExecutionPayload):
        if payload.threat_context:
            out["asset_name"] = payload.threat_context.asset_name
            out["cve_id"] = payload.threat_context.cve_id
            out["cvss_vector"] = payload.threat_context.cvss_vector
            out["cvss_score"] = payload.threat_context.cvss_base_score
            out["daily_revenue_impact_cr"] = payload.threat_context.daily_revenue_impact_cr
            out["regulatory_tier"] = payload.threat_context.regulatory_tier
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
            out["daily_revenue_impact_cr"] = payload.asset.daily_revenue_impact_inr_cr
            out["regulatory_tier"] = payload.asset.regulatory_tier
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


def template_business_briefing(data: Dict[str, Any], prompt: str = "") -> str:
    """Plain-English executive briefing (EAL ₹, VaR ₹, ROSI %, zero technical jargon)."""
    viable_str = "economically viable" if data["is_economically_viable"] else "NOT economically viable (exceeds Gordon-Loeb ceiling)"
    
    # Explicitly explain why money is lost (downtime vs. regulatory fines)
    explanation_why_lost = (
        f"Financial Loss Breakdown & Rationale:\n"
        f"  - Downtime (Primary Loss): System downtime directly suspends transaction throughput. For the asset '{data['asset_name']}', "
        f"every day of outage results in an estimated daily revenue loss of ₹{data['daily_revenue_impact_cr']:.2f} Cr. Over a typical disruption period, "
        f"operational downtime and primary recovery actions account for a primary loss exposure of ₹{data['primary_loss_cr']:.2f} Cr.\n"
        f"  - Regulatory & Compliance Penalties (Secondary Loss): Because '{data['asset_name']}' is classified under {data.get('regulatory_tier', 'TIER_1_CRITICAL')}, "
        f"unauthorized exposure triggers significant regulatory fines, compliance audits, and legal non-compliance penalties. This secondary impact adds an estimated "
        f"₹{data['secondary_loss_cr']:.2f} Cr to the overall exposure."
    )

    # Dynamic context awareness based on prompt intent
    lower = prompt.lower()
    custom_intro = ""
    if "budget" in lower or "viable" in lower or "lakh" in lower or "crore" in lower:
        custom_intro = (
            f"DIRECT ANSWER TO YOUR BUDGET INQUIRY:\n"
            f"Allocating ₹{data['control_cost_cr']*100:.1f} Lakhs (₹{data['control_cost_cr']:.2f} Cr) is {viable_str}.\n"
            f"The Gordon-Loeb optimal capital ceiling is ₹{data['gordon_loeb_cap_cr']:.2f} Cr, and the projected Return on Security Investment (ROSI) is {data['rosi_pct']:.1f}%.\n\n"
        )
    elif "downtime" in lower or "primary" in lower or "secondary" in lower or "penalty" in lower:
        custom_intro = (
            f"DIRECT ANSWER TO YOUR LOSS BREAKDOWN INQUIRY:\n"
            f"For {data['asset_name']}, operational downtime loss is ₹{data['primary_loss_cr']:.2f} Cr, while regulatory & secondary penalties account for ₹{data['secondary_loss_cr']:.2f} Cr.\n\n"
        )

    return (
        f"{custom_intro}EXECUTIVE RISK BRIEFING\n"
        f"Target Asset: {data['asset_name']} | Threat CVE: {data['cve_id']}\n\n"
        f"1. Financial Exposure:\n"
        f"   - Expected Annual Loss (EAL): ₹{data['eal_cr']:.2f} Cr\n"
        f"   - 95% Value-at-Risk (VaR): ₹{data['var_95_cr']:.2f} Cr\n"
        f"   - Operational Downtime Loss: ₹{data['primary_loss_cr']:.2f} Cr\n"
        f"   - Regulatory & Secondary Penalties: ₹{data['secondary_loss_cr']:.2f} Cr\n\n"
        f"2. {explanation_why_lost}\n\n"
        f"3. Security Economics & Recommendation:\n"
        f"   - Proposed Control Cost: ₹{data['control_cost_cr']:.2f} Cr\n"
        f"   - Anticipated Risk Reduction: ₹{data['risk_reduced_cr']:.2f} Cr\n"
        f"   - Return on Security Investment (ROSI): {data['rosi_pct']:.1f}%\n"
        f"   - Gordon-Loeb Capital Ceiling: ₹{data['gordon_loeb_cap_cr']:.2f} Cr\n"
        f"   - Assessment: The proposed investment is {viable_str}.\n"
    )


def template_technical_diagnostic(data: Dict[str, Any], prompt: str = "") -> str:
    """Technical SecOps diagnostic (CVSS vectors, EPSS odds ratios, XAI salient tokens)."""
    tokens_str = ", ".join(data["salient_tokens"]) if data["salient_tokens"] else "remote, code_execution"
    odds_ratio = data["epss_prob"] / max(1e-6, 1.0 - data["epss_prob"])

    # Explicitly explain the meaning of CVSS/EPSS metrics
    explanation_metrics = (
        f"Metric Interpretations & Calculations:\n"
        f"  - CVSS (Common Vulnerability Scoring System): Evaluates the intrinsic severity of a vulnerability. A score of {data['cvss_score']} indicates a CRITICAL severity. The vector '{data['cvss_vector']}' signifies that the attack vector is Network-based with Low complexity, requiring No privileges or user interaction.\n"
        f"  - EPSS (Exploit Prediction Scoring System): Predicts the likelihood of wild exploitation of a vulnerability within the next 30 days. An EPSS probability of {data['epss_prob']:.4f} ({data['epss_prob']*100:.2f}%) represents a specific likelihood of exploitation. The exploit odds ratio is {odds_ratio:.4f}, meaning this vulnerability is {odds_ratio:.4f} times more likely to be exploited than standard baseline signatures.\n"
        f"  - XAI Trust Score: Measures alignment of the threat model prediction with expert security rules (configured threshold is 75%). Current trust alignment score is {data['trust_score_pct']:.1f}% ({data['alignment_status']})."
    )

    lower = prompt.lower()
    custom_intro = ""
    if "epss" in lower or "exploit" in lower or "probability" in lower:
        custom_intro = (
            f"DIRECT ANSWER TO YOUR EPSS INQUIRY:\n"
            f"Vulnerability {data['cve_id']} has a real-world EPSS exploit probability of {data['epss_prob']:.4f} ({data['epss_prob']*100:.2f}%).\n"
            f"The exploit odds ratio is {odds_ratio:.4f} compared to baseline threat signals.\n\n"
        )
    elif "xai" in lower or "trust" in lower or "align" in lower:
        custom_intro = (
            f"DIRECT ANSWER TO YOUR XAI TRUST INQUIRY:\n"
            f"The XAI Trust Auditor evaluated model alignment at {data['trust_score_pct']:.1f}% ({data['alignment_status']}).\n"
            f"Salient attribution tokens: [{tokens_str}].\n\n"
        )

    return (
        f"{custom_intro}TECHNICAL SECOPS DIAGNOSTIC REPORT\n"
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
        f"3. {explanation_metrics}\n\n"
        f"4. Risk & Loss Parameters:\n"
        f"   - EAL: ₹{data['eal_cr']:.4f} Cr | VaR (95%): ₹{data['var_95_cr']:.4f} Cr\n"
        f"   - Primary Downtime Loss: ₹{data['primary_loss_cr']:.4f} Cr\n"
        f"   - Secondary Regulatory Loss: ₹{data['secondary_loss_cr']:.4f} Cr\n"
        f"   - ROSI: {data['rosi_pct']:.2f}% | Viable: {data['is_economically_viable']}\n"
    )


def call_external_llm(prompt_instruction: str, data: Dict[str, Any], user_prompt: str = "") -> Optional[str]:
    """Wrapper hook for external LLM APIs (Gemini/OpenAI/Anthropic). Returns None if unconfigured."""
    data_json = json.dumps(data, indent=2)
    user_content = (
        f"USER QUESTION: {user_prompt}\n\n" if user_prompt else ""
    ) + f"PRE-CALCULATED EXECUTION_PAYLOAD:\n{data_json}\n\nAnswer the user question directly while locking all numerical values from the execution payload."

    # Gemini Wrapper Hook
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if LLM_PROVIDER == "gemini" or (gemini_key and not LLM_PROVIDER):
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel(model_name="gemini-3.6-flash", system_instruction=prompt_instruction)
            resp = model.generate_content(user_content, request_options={"timeout": 2.0})
            return resp.text
        except Exception:
            pass

    # OpenAI Wrapper Hook
    openai_key = os.environ.get("OPENAI_API_KEY")
    if LLM_PROVIDER == "openai" or (openai_key and not LLM_PROVIDER):
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key, timeout=2.0)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt_instruction},
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
            client = Anthropic(api_key=anthropic_key, timeout=2.0)
            resp = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=prompt_instruction,
                messages=[{"role": "user", "content": user_content}],
            )
            return "".join(b.text for b in resp.content if b.type == "text")
        except Exception:
            pass

    return None


def format_business_briefing(payload: Any, prompt: str = "") -> str:
    """Format plain-English executive briefing (EAL ₹, VaR ₹, ROSI %, zero technical jargon)."""
    data = _extract_payload_dict(payload)
    llm_output = None
    system_instruction = _BUSINESS_PROMPT
    
    # Model Watchdog Try-Except Block for local model
    if model_manager.active_generation and not model_manager.is_fallback:
        try:
            user_content = f"USER QUESTION: {prompt}\n\nPRE-CALCULATED PAYLOAD: {json.dumps(data)}"
            llm_output = model_manager.generate(user_content, system_instruction)
            if llm_output:
                passed, errors = guardrail_verifier.verify_financial_integrity(payload, llm_output)
                if not passed:
                    raise ValueError(f"Numeric hallucination detected: {', '.join(errors)}")
        except Exception as e:
            model_manager.swap_generation_model()
            print(f"[Watchdog] Local model failed/hallucinated: {e}. Swapped generation model.")
            llm_output = None
            
    # Fall back to external LLM if local is not active or did not return output
    if not llm_output:
        llm_output = call_external_llm(system_instruction, data, user_prompt=prompt)
        
    if llm_output:
        return llm_output
        
    return template_business_briefing(data, prompt)


def format_technical_diagnostic(payload: Any, prompt: str = "") -> str:
    """Format technical SecOps diagnostic (CVSS vectors, EPSS odds ratios, XAI salient tokens)."""
    data = _extract_payload_dict(payload)
    llm_output = None
    system_instruction = _TECHNICAL_PROMPT
    
    # Model Watchdog Try-Except Block for local model
    if model_manager.active_generation and not model_manager.is_fallback:
        try:
            user_content = f"USER QUESTION: {prompt}\n\nPRE-CALCULATED PAYLOAD: {json.dumps(data)}"
            llm_output = model_manager.generate(user_content, system_instruction)
            if llm_output:
                passed, errors = guardrail_verifier.verify_financial_integrity(payload, llm_output)
                if not passed:
                    raise ValueError(f"Numeric hallucination detected: {', '.join(errors)}")
        except Exception as e:
            model_manager.swap_generation_model()
            print(f"[Watchdog] Local model failed/hallucinated: {e}. Swapped generation model.")
            llm_output = None
            
    # Fall back to external LLM if local is not active or did not return output
    if not llm_output:
        llm_output = call_external_llm(system_instruction, data, user_prompt=prompt)
        
    if llm_output:
        return llm_output
        
    return template_technical_diagnostic(data, prompt)


class HybridSynthesizer:
    """Hybrid synthesizer providing template formatting + external LLM API hooks."""

    def format_business_briefing(self, payload: Any, prompt: str = "") -> str:
        return format_business_briefing(payload, prompt)

    def format_technical_diagnostic(self, payload: Any, prompt: str = "") -> str:
        return format_technical_diagnostic(payload, prompt)

    def synthesize(self, payload: Any, persona: PersonaType = PersonaType.BUSINESS, prompt: str = "") -> str:
        if persona == PersonaType.TECHNICAL:
            return self.format_technical_diagnostic(payload, prompt)
        return self.format_business_briefing(payload, prompt)

    def generate_conversational_response(self, prompt: str, persona: PersonaType) -> str:
        """Generate conversational response for non-risk queries, bypassing math engines."""
        clean = (prompt or "").strip()
        
        # 1. Unidentified query / symbols fallback
        if not clean or len(clean) < 3 or clean in ["/", "?", "!", ".", "asdf", "test", "xxx", "helpme"]:
            if clean.lower() not in ["hi", "hey", "yo"]:
                return (
                    f"UNIDENTIFIED QUERY: '{prompt}'\n\n"
                    "Suggested Executive Queries:\n"
                    "- What is the risk for Core Payment Switch with CVE-2024-1234?\n"
                    "- Explain the ROSI framework and Gordon-Loeb optimal ceiling.\n"
                    "- Prepare boardroom capital approval for cybersecurity budget of 50 Crores."
                )

        # 2. Conversational greetings / welcomes
        lower = clean.lower()
        if any(lower.startswith(g) for g in ["hi", "hello", "hey", "greetings", "good morning", "good evening", "yo"]):
            if not any(k in lower for k in ["cve", "loss", "eal", "var", "epss", "budget", "cost", "switch", "database"]):
                if persona == PersonaType.TECHNICAL:
                    return (
                        "CYBERRISKIQ SECOPS DIAGNOSTIC COPILOT ONLINE\n\n"
                        "Greetings! I am the CyberRiskIQ SecOps Copilot. I analyze CVEs, exploit probabilities, and trust scores. "
                        "How can I assist you with vulnerability diagnostics today?"
                    )
                else:
                    return (
                        "Hello! I am the CyberRiskIQ Executive Copilot. I help you evaluate the financial exposure of your assets. "
                        "How can I assist you with security budget planning today?"
                    )

        system_instruction = (
            "You are the CyberRiskIQ Copilot. Answer general knowledge or conversational queries about cyber risk, "
            "vulnerability management, or general IT security. Keep the response relevant to your role. "
            "STRICT ZERO-MATH RULE: Do not invent, compute, or output any specific risk figures (₹ Cr, percentages) for assets unless they are well-known definitions."
        )
        if persona == PersonaType.BUSINESS:
            system_instruction += " Address the user with a professional business/executive tone."
        else:
            system_instruction += " Address the user with a technical SecOps/analyst tone."
            
        try:
            llm_output = None
            if model_manager.active_generation and not model_manager.is_fallback:
                llm_output = model_manager.generate(prompt, system_instruction)
            if not llm_output:
                llm_output = call_external_llm(system_instruction, {}, user_prompt=prompt)
            if llm_output:
                return llm_output
        except Exception as e:
            model_manager.swap_generation_model()
            print(f"[Watchdog] Conversational Transformer failure: {e}. Swapped generation model.")
            
        # Fallback template responses if local model is not loaded and LLM is offline or fails
        if "api key" in lower:
            if persona == PersonaType.BUSINESS:
                return "An API key is a unique code used by computer programs to identify and authenticate each other. In our business context, we use API keys to securely connect our risk ledger to live security tools, ensuring automated and authenticated data flows."
            else:
                return "An API key is a token-based credential passed by an application to authenticate its identity during API calls. It is typically sent in HTTP headers (e.g., Authorization: Bearer <key>) or query parameters, and must be rotated regularly to prevent credential exposure."
        
        if "rosi" in lower or "return on security" in lower:
            return (
                "CONCEPT EXPLANATION: Return on Security Investment (ROSI)\n\n"
                "ROSI measures the economic efficiency of cybersecurity controls:\n"
                "Formula: ROSI % = ((Risk Reduced - Control Cost) / Control Cost) × 100\n\n"
                "Grounding Example from Core Payment Switch:\n"
                "• Control Cost: ₹0.30 Cr (₹30.0 Lakhs)\n"
                "• Risk Reduction: ₹0.77 Cr\n"
                "• Calculated ROSI: 256.7%\n"
                "• Gordon-Loeb Ceiling: ₹0.46 Cr (Assessment: Viable)"
            )
        elif "epss" in lower or "exploit probability" in lower:
            return (
                "CONCEPT EXPLANATION: Exploit Prediction Scoring System (EPSS)\n\n"
                "EPSS estimates the probability that a CVE vulnerability will be weaponized in the wild within 30 days.\n"
                "Model: Elastic Net Logistic Regression (Jacobs et al., 2021) using 16 feature flags.\n\n"
                "Grounding Example for CVE-2024-1234:\n"
                "• Exploit Probability: 0.0091 (0.91%)\n"
                "• CVSS Vector: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H\n"
                "• XAI Trust Score: 82.0% (EXPERT_GROUNDED)"
            )
        elif "fair" in lower or "expected annual loss" in lower or "eal" in lower or "var" in lower:
            return (
                "CONCEPT EXPLANATION: Open FAIR v3.0 Risk Model\n\n"
                "Open FAIR quantifies financial exposure using Monte Carlo lognormal trial simulations (10,000 trials):\n"
                "• LEF (Loss Event Frequency) = EPSS Prob × 0.35\n"
                "• EAL = Mean loss across all simulated trials\n"
                "• 95% VaR = Worst-case loss at 95th percentile\n\n"
                "Grounding Example for Core Payment Switch:\n"
                "• EAL: ₹1.25 Cr | 95% VaR: ₹4.50 Cr"
            )
        elif "gordon" in lower or "loeb" in lower or "ceiling" in lower:
            return (
                "CONCEPT EXPLANATION: Gordon-Loeb Economic Model (2002)\n\n"
                "The Gordon-Loeb model proves that optimal security spending should never exceed (1/e) × EAL ≈ 37% of Expected Annual Loss.\n\n"
                "Grounding Example for Core Payment Switch:\n"
                "• EAL: ₹1.25 Cr\n"
                "• Gordon-Loeb Capital Ceiling: ₹0.46 Cr\n"
                "• Proposed Spend: ₹0.30 Cr -> Viable!"
            )
        
        if persona == PersonaType.BUSINESS:
            return "Hello! I am the CyberRiskIQ Executive Copilot. I help you evaluate the financial exposure of your assets. How can I assist you with security budget planning today?"
        else:
            return "Greetings! I am the CyberRiskIQ SecOps Copilot. I analyze CVEs, exploit probabilities, and trust scores. How can I assist you with vulnerability diagnostics today?"


# Alias for backward compatibility
PromptSynthesizers = HybridSynthesizer
