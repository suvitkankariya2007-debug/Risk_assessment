import re
import json
from typing import Dict, Any, List, Optional, Tuple
from schemas.data_models import DeterministicContextPayload


class SanityGuardrailVerifier:
    MONETARY_PATTERN = re.compile(r"([A-Za-z0-9% -]+):\s*(?:[\₹$])?[\s]*([0-9,]+\.[0-9]+|\d+)(?:\s*(?:%|Crores?|Crore|Lakhs?|Lakh|Cr|L|Rs|INR))?")

    def verify(self, payload: DeterministicContextPayload, output_text: str) -> tuple[bool, List[str]]:
        errors: List[str] = []
        numbers = self._extract_line_numbers(output_text)
        expected = self._build_expected_map(payload)
        for key, expected_val in expected.items():
            actual = numbers.get(key)
            if actual is None:
                errors.append(f"Missing expected value for {key} in output text")
            elif abs(float(actual) - float(expected_val)) > 0.05:
                errors.append(f"Mismatch {key}: text={actual}, payload={expected_val}")
        return len(errors) == 0, errors

    def _extract_line_numbers(self, text: str) -> Dict[str, float]:
        found: Dict[str, float] = {}
        for m in self.MONETARY_PATTERN.finditer(text):
            label = m.group(1).strip()
            num_str = m.group(2).replace(",", "")
            try:
                val = float(num_str)
            except ValueError:
                continue
            mapped = self._map_label(label)
            if mapped:
                found[mapped] = val
        return found

    @staticmethod
    def _map_label(label: str) -> Optional[str]:
        l = label.lower()
        if "expected annual loss" in l or l == "eal":
            return "EAL"
        if "value-at-risk" in l or "var" in l:
            return "VaR"
        if l == "rosi":
            return "ROSI"
        if "net capital saved" in l:
            return "Net Capital Saved"
        if "control cost" in l:
            return "Control Cost"
        if "risk reduced" in l:
            return "Risk Reduced"
        if "gordon-loeb" in l or "ceiling" in l:
            return "Gordon-Loeb Ceiling"
        if l == "primary loss":
            return "Primary Loss"
        if l == "secondary loss":
            return "Secondary Loss"
        return None

    def _build_expected_map(self, payload: DeterministicContextPayload) -> Dict[str, float]:
        m: Dict[str, float] = {}
        if payload.fair:
            m["EAL"] = payload.fair.eal_inr_cr
            m["VaR"] = payload.fair.var_95_inr_cr
            m["Primary Loss"] = payload.fair.primary_loss_inr_cr
            m["Secondary Loss"] = payload.fair.secondary_loss_inr_cr
        if payload.milprosi:
            m["ROSI"] = payload.milprosi.rosi_pct
            m["Net Capital Saved"] = payload.milprosi.net_capital_saved_inr_cr
            m["Control Cost"] = payload.milprosi.control_cost_inr_cr
            m["Risk Reduced"] = payload.milprosi.risk_reduced_inr_cr
            m["Gordon-Loeb Ceiling"] = payload.milprosi.gordon_loeb_ceiling_inr_cr
        return m
