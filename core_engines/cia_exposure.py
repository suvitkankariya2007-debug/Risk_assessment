"""
core_engines/cia_exposure.py
============================
CIA-triad (Confidentiality / Integrity / Availability) based exposure and
annualized loss. Replaces the hardcoded z_score = -1.5 placeholder with a
genuinely computed security-posture figure.

Formulas:
    Exposure = 1 - avg(C, I, A)         (each 0-1 → Exposure in [0, 1])
    ALE      = Exposure * SegImpact     (₹ Cr)
"""
from pydantic import ConfigDict

from schemas.data_models import CiaExposureResult


class CIAExposureEngine:
    """Exposure/ALE engine derived from current CIA control scores."""

    def __init__(self) -> None:
        # Silence unused-import linters while keeping the strict-config import
        # meaningful for schema parity checks in tests.
        _ = ConfigDict

    def evaluate(self, confidentiality: float, integrity: float, availability: float, seg_impact_cr: float) -> CiaExposureResult:
        """
        Args:
            confidentiality/integrity/availability: current-control scores,
                each a float in [0, 1] (1 = fully protected).
            seg_impact_cr: Segment financial impact in ₹ Cr (from segment_risk).

        Raises:
            ValueError: If any CIA score is outside [0, 1] or SegImpact < 0.
        """
        scores = {
            "confidentiality": confidentiality,
            "integrity": integrity,
            "availability": availability,
        }
        for name, val in scores.items():
            val = float(val)
            if not (0.0 <= val <= 1.0):
                raise ValueError(f"{name} must be in [0, 1], got {val}")
        seg_impact_cr = float(seg_impact_cr)
        if seg_impact_cr < 0:
            raise ValueError(f"seg_impact_cr must be >= 0, got {seg_impact_cr}")

        c = float(confidentiality)
        i = float(integrity)
        a = float(availability)

        # Exposure = 1 - avg(CIA)
        exposure = 1.0 - ((c + i + a) / 3.0)

        # Invariant: Exposure is always in [0, 1]
        assert 0.0 <= exposure <= 1.0, f"Exposure {exposure} outside [0, 1]"

        # ALE = Exposure * SegImpact
        ale_cr = exposure * seg_impact_cr

        return CiaExposureResult(
            confidentiality=round(c, 4),
            integrity=round(i, 4),
            availability=round(a, 4),
            exposure=round(exposure, 4),
            seg_impact_cr=round(seg_impact_cr, 4),
            ale_cr=round(ale_cr, 4),
        )


def compute_cia_exposure(
    confidentiality: float,
    integrity: float,
    availability: float,
    seg_impact_cr: float,
) -> CiaExposureResult:
    """Module-level wiring shim used by api_layer/dual_routes.py.

    Delegates straight to CIAExposureEngine.evaluate — no math here.
    """
    return CIAExposureEngine().evaluate(
        confidentiality=confidentiality,
        integrity=integrity,
        availability=availability,
        seg_impact_cr=seg_impact_cr,
    )
