from __future__ import annotations

from backend.data import BASELINE_EAL_LAKHS, DIGITAL_ASSETS, MITIGATION_ACTIONS, REGULATORY_COMPLIANCE
from backend.math_engine import calculate_scenario, optimize_budget


PERSONA_TEMPLATES = {
    "Executive": "Answer with concise business impact and recommended action based only on the supplied metrics.",
    "CISO": "Answer with operational risk prioritization and control-gap focus using the verified numbers only.",
    "Analyst": "Answer with evidence-first, numerically grounded reasoning and explicit assumptions.",
}


def _build_system_context() -> str:
    baseline_eal = float(BASELINE_EAL_LAKHS)
    top_asset = max(DIGITAL_ASSETS, key=lambda asset: float(asset["baseline_eal_lakhs"]))
    scenario = calculate_scenario([str(action["id"]) for action in MITIGATION_ACTIONS if action["default_on"]])
    optimizer = optimize_budget(120.0)
    compliance_summary = "; ".join(f"{name}: {meta['score']}%" for name, meta in REGULATORY_COMPLIANCE.items())

    return "\n".join(
        [
            "SYSTEM STATE (VERIFIED NUMBERS ONLY)",
            f"Baseline org EAL: ₹{baseline_eal:.2f}L",
            f"Default-enabled scenario projected EAL: ₹{scenario.projected_eal_lakhs:.2f}L",
            f"Default-enabled scenario reduction: ₹{scenario.reduction_lakhs:.2f}L",
            f"Budget optimization at ₹120L recommends: {optimizer.recommended_action_ids}",
            f"Top risk asset: {top_asset['name']} in {top_asset['business_unit']} at ₹{top_asset['baseline_eal_lakhs']:.2f}L",
            f"Compliance scores: {compliance_summary}",
        ]
    )


def ask_copilot(query: str, persona: str) -> str:
    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    normalized_persona = persona.strip().title()
    if normalized_persona not in PERSONA_TEMPLATES:
        normalized_persona = "Executive"

    context = _build_system_context()
    return (
        f"{PERSONA_TEMPLATES[normalized_persona]}\n\n"
        f"Strict system context:\n{context}\n\n"
        f"User query: {query}\n\n"
        "Answer using only the supplied numbers and keep the response plain text."
    )


__all__ = ["ask_copilot", "PERSONA_TEMPLATES"]
