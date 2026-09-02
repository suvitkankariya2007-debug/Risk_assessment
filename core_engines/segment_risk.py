"""
core_engines/segment_risk.py
============================
Segment-level financial impact and actual (not worst-case) segment risk.

Formulas (implemented EXACTLY as specified — no extra terms):
    Impact_w   = Impact_Operational * Impact_Financial        (each 0-10)
    SegImpact  = SegRevenue * Impact_w                        (₹ Cr)
    SegRisk    = SegImpact * (Impact_w * Risk_w)              (₹ Cr)

Note: because Impact_w ranges 0-100 and Risk_w 0-10 under the literal spec,
SegRisk <= SegImpact holds exactly when (Impact_w * Risk_w) <= 1. This
boundary is surfaced to the caller via `risk_weighting_factor` instead of a
silent clamp — per the no-silent-fixup rule.
"""
from schemas.data_models import SegmentRiskResult


class SegmentRiskEngine:
    """Segment impact/risk calculator over caller-supplied threat inputs."""

    @staticmethod
    def _validate_0_10(name: str, value: float) -> float:
        value = float(value)
        if not (0.0 <= value <= 10.0):
            raise ValueError(f"{name} must be in [0, 10], got {value}")
        return value

    def evaluate(
        self,
        seg_revenue_cr: float,
        impact_operational: float,
        impact_financial: float,
        risk_w: float,
    ) -> SegmentRiskResult:
        """
        Args:
            seg_revenue_cr: SegRevenue = revenue_pct/100 * unit annual revenue (₹ Cr).
            impact_operational: Impact_Operational score, 0-10 (caller-supplied).
            impact_financial: Impact_Financial score, 0-10 (caller-supplied).
            risk_w: Risk_w likelihood/success-rate of the threat, 0-10 (caller-supplied).

        Raises:
            ValueError: If any input violates its declared range.
        """
        if seg_revenue_cr < 0:
            raise ValueError(f"seg_revenue_cr must be >= 0, got {seg_revenue_cr}")
        impact_operational = self._validate_0_10("impact_operational", impact_operational)
        impact_financial = self._validate_0_10("impact_financial", impact_financial)
        risk_w = self._validate_0_10("risk_w", risk_w)

        # Impact_w = Impact_Operational * Impact_Financial
        impact_w = impact_operational * impact_financial

        # SegImpact = SegRevenue * Impact_w
        seg_impact_cr = seg_revenue_cr * impact_w

        # SegRisk = SegImpact * (Impact_w * Risk_w)
        risk_weighting_factor = impact_w * risk_w
        seg_risk_cr = seg_impact_cr * risk_weighting_factor

        return SegmentRiskResult(
            impact_operational=impact_operational,
            impact_financial=impact_financial,
            impact_w=round(impact_w, 4),
            seg_revenue_cr=round(float(seg_revenue_cr), 4),
            seg_impact_cr=round(seg_impact_cr, 4),
            risk_w=risk_w,
            seg_risk_cr=round(seg_risk_cr, 4),
            risk_weighting_factor=round(risk_weighting_factor, 4),
        )


def compute_segment_risk(
    impact_operational: float,
    impact_financial: float,
    seg_revenue_cr: float,
    risk_w: float,
) -> SegmentRiskResult:
    """Module-level wiring shim used by api_layer/dual_routes.py.

    Delegates straight to SegmentRiskEngine.evaluate — no math here.
    """
    return SegmentRiskEngine().evaluate(
        seg_revenue_cr=seg_revenue_cr,
        impact_operational=impact_operational,
        impact_financial=impact_financial,
        risk_w=risk_w,
    )
