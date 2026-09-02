"""
api_layer/guardrails.py
========================
SanityGuardrailVerifier for financial and numerical integrity.

Scans synthesized LLM/template text using regex matching for ₹ currency figures
and percentages against the pre-calculated ExecutionPayload. Blocks responses
with hallucinated numbers or Gordon-Loeb contradictions.
"""
import re
from typing import Any, List, Tuple, Dict, Set
from schemas.data_models import ExecutionPayload, DeterministicContextPayload

_CURRENCY_REGEX = re.compile(
    r"(?:₹|\bINR\b|\bRs\.?)\s*([0-9,]+\.?[0-9]*)\s*(?:Cr|Crores?|Lakhs?|L)?",
    re.IGNORECASE,
)
_PERCENT_REGEX = re.compile(r"([0-9,]+\.?[0-9]*)\s*%", re.IGNORECASE)


def _collect_payload_numbers(payload: Any) -> Set[float]:
    """Collect all valid numeric values from either ExecutionPayload or DeterministicContextPayload."""
    nums: Set[float] = set()

    if isinstance(payload, ExecutionPayload):
        if payload.threat_context:
            nums.add(round(payload.threat_context.asset_replacement_cost_cr, 2))
            nums.add(round(payload.threat_context.daily_revenue_impact_cr, 2))
            nums.add(round(payload.threat_context.cvss_base_score, 1))
            nums.add(round(payload.threat_context.proposed_control_cost_lakhs, 2))
            # Proposed control cost in Crore
            nums.add(round(payload.threat_context.proposed_control_cost_lakhs / 100.0, 2))
            # Proposed control cost in Lakhs
            nums.add(round(payload.threat_context.proposed_control_cost_lakhs, 1))
        if payload.fair_result:
            nums.add(round(payload.fair_result.expected_annual_loss_cr, 2))
            nums.add(round(payload.fair_result.value_at_risk_95_cr, 2))
            nums.add(round(payload.fair_result.primary_loss_cr, 2))
            nums.add(round(payload.fair_result.secondary_loss_cr, 2))
            nums.add(round(payload.fair_result.expected_annual_loss_cr, 4))
            nums.add(round(payload.fair_result.value_at_risk_95_cr, 4))
        if payload.epss_prediction:
            nums.add(round(payload.epss_prediction.epss_probability, 4))
            nums.add(round(payload.epss_prediction.epss_probability * 100.0, 2))
            nums.add(round(payload.epss_prediction.percentile, 2))
        if payload.xai_trust:
            nums.add(round(payload.xai_trust.trust_score_pct, 1))
            nums.add(round(payload.xai_trust.trust_score_pct, 2))
        if payload.rosi_result:
            nums.add(round(payload.rosi_result.control_cost_cr, 2))
            nums.add(round(payload.rosi_result.risk_reduced_cr, 2))
            nums.add(round(payload.rosi_result.net_benefit_cr, 2))
            nums.add(round(payload.rosi_result.rosi_percentage, 1))
            nums.add(round(payload.rosi_result.rosi_percentage, 2))
            nums.add(round(payload.rosi_result.gordon_loeb_cap_cr, 2))
            nums.add(round(payload.rosi_result.control_cost_cr, 4))
            nums.add(round(payload.rosi_result.gordon_loeb_cap_cr, 4))

    elif isinstance(payload, DeterministicContextPayload):
        if payload.asset:
            nums.add(round(payload.asset.hardware_replacement_cost_inr_cr, 2))
            nums.add(round(payload.asset.daily_revenue_impact_inr_cr, 2))
            nums.add(round(payload.asset.criticality_score, 1))
        if payload.fair:
            nums.add(round(payload.fair.eal_inr_cr, 2))
            nums.add(round(payload.fair.var_95_inr_cr, 2))
            nums.add(round(payload.fair.primary_loss_inr_cr, 2))
            nums.add(round(payload.fair.secondary_loss_inr_cr, 2))
            nums.add(round(payload.fair.eal_inr_cr, 4))
            nums.add(round(payload.fair.var_95_inr_cr, 4))
        if payload.epss:
            nums.add(round(payload.epss.p_exploit, 4))
            nums.add(round(payload.epss.p_exploit * 100.0, 2))
        if payload.xai:
            nums.add(round(payload.xai.trust_score_pct, 1))
            nums.add(round(payload.xai.trust_score_pct, 2))
        if payload.milprosi:
            nums.add(round(payload.milprosi.control_cost_inr_cr, 2))
            nums.add(round(payload.milprosi.risk_reduced_inr_cr, 2))
            nums.add(round(payload.milprosi.net_capital_saved_inr_cr, 2))
            nums.add(round(payload.milprosi.rosi_pct, 1))
            nums.add(round(payload.milprosi.rosi_pct, 2))
            nums.add(round(payload.milprosi.gordon_loeb_ceiling_inr_cr, 2))

    elif isinstance(payload, dict):
        for v in payload.values():
            if isinstance(v, (int, float)):
                nums.add(round(float(v), 2))
                nums.add(round(float(v), 4))

    return nums


def _is_number_grounded(val: float, valid_nums: Set[float], tolerance: float = 0.08) -> bool:
    """Check if extracted number matches any expected figure in the payload within tolerance."""
    if val == 0.0:
        return True
    for expected in valid_nums:
        if expected == 0.0:
            continue
        if abs(val - expected) < 0.05 or abs(val - expected) / abs(expected) <= tolerance:
            return True
    return False


class SanityGuardrailVerifier:
    """Scans synthesized text against ExecutionPayload to block hallucinated numbers."""

    def verify_financial_integrity(self, payload: Any, output_text: Any = None) -> Tuple[bool, List[str]]:
        """
        Verify that all ₹ currency figures and percentages in output_text exist in payload.

        Supports arguments passed as (payload, output_text) or (output_text, payload).
        """
        if isinstance(payload, str) and not isinstance(output_text, str):
            payload, output_text = output_text, payload

        text = output_text or ""
        valid_nums = _collect_payload_numbers(payload)
        errors: List[str] = []

        # Check currency matches
        for m in _CURRENCY_REGEX.finditer(text):
            num_str = m.group(1).replace(",", "")
            try:
                val = float(num_str)
            except ValueError:
                continue
            if not _is_number_grounded(val, valid_nums):
                errors.append(f"Hallucinated ₹ currency figure detected: '{m.group(0)}' (val={val})")

        # Check percentage matches
        for m in _PERCENT_REGEX.finditer(text):
            num_str = m.group(1).replace(",", "")
            try:
                val = float(num_str)
            except ValueError:
                continue
            # Ignore standard common percentages like 95% (from VaR 95%) or 100%
            if val in (95.0, 100.0, 0.0):
                continue
            if not _is_number_grounded(val, valid_nums):
                errors.append(f"Hallucinated percentage figure detected: '{m.group(0)}' (val={val})")

        # Check Gordon-Loeb economic viability consistency
        is_viable = None
        if isinstance(payload, ExecutionPayload):
            if payload.rosi_result:
                is_viable = payload.rosi_result.is_economically_viable
            # Check Phase-1 extensions for ExecutionPayload
            _add_phase1_extensions(payload, valid_nums)
        elif isinstance(payload, DeterministicContextPayload):
            if payload.milprosi:
                is_viable = payload.milprosi.is_economically_viable
            # Check Phase-1 extensions for DeterministicContextPayload
            _add_phase1_extensions(payload, valid_nums)

        if is_viable is False:
            text_lower = text.lower()
            if "economically viable" in text_lower and "not economically viable" not in text_lower:
                errors.append("Contradiction: Response claims spend is economically viable, but Gordon-Loeb ceiling is exceeded.")

        # Banned-token lint (Phase 2)
        banned_tokens = ["100% secure", "hack-proof", "guarantee", "bulletproof", "unhackable", "invulnerable"]
        text_lower = text.lower()
        for token in banned_tokens:
            if token in text_lower:
                errors.append(f"Banned token detected: '{token}'. Do not make absolute security claims.")

        passed = len(errors) == 0
        return passed, errors

def _add_phase1_extensions(payload: Any, nums: Set[float]) -> None:
    if getattr(payload, "business_profile", None):
        nums.add(round(payload.business_profile.total_revenue_cr, 2))
    if getattr(payload, "segment_risk", None):
        nums.add(round(payload.segment_risk.seg_revenue_cr, 2))
        nums.add(round(payload.segment_risk.seg_impact_cr, 2))
        nums.add(round(payload.segment_risk.seg_risk_cr, 2))
        nums.add(round(payload.segment_risk.impact_operational, 2))
        nums.add(round(payload.segment_risk.impact_financial, 2))
        nums.add(round(payload.segment_risk.risk_w, 2))
        nums.add(round(payload.segment_risk.impact_w, 2))
    if getattr(payload, "control_maturity", None):
        nums.add(round(payload.control_maturity.maturity_multiplier, 2))
        nums.add(round(payload.control_maturity.efficacy_t, 2))
        nums.add(round(payload.control_maturity.control_efficacy_t, 2))
    if getattr(payload, "rosi_v2", None):
        nums.add(round(payload.rosi_v2.ale_cr, 2))
        nums.add(round(payload.rosi_v2.z_rosi, 2))
        nums.add(round(payload.rosi_v2.z_rosi, 1))
        nums.add(round(payload.rosi_v2.cost_rate, 2))
    if getattr(payload, "cia_exposure", None):
        nums.add(round(payload.cia_exposure.confidentiality, 2))
        nums.add(round(payload.cia_exposure.integrity, 2))
        nums.add(round(payload.cia_exposure.availability, 2))
        nums.add(round(payload.cia_exposure.exposure, 2))
        nums.add(round(payload.cia_exposure.ale_cr, 2))
    if getattr(payload, "domain_priority", None):
        for dp in payload.domain_priority:
            nums.add(round(dp.d_priority, 2))
            nums.add(round(dp.impact_weight, 2))

    def verify(self, payload: Any, output_text: Any = None) -> Tuple[bool, List[str]]:
        """Alias for verify_financial_integrity."""
        return self.verify_financial_integrity(payload, output_text)


def validate(response_text: str, payload: Any) -> Tuple[bool, List[str]]:
    """Module-level function alias."""
    verifier = SanityGuardrailVerifier()
    return verifier.verify_financial_integrity(payload, response_text)
