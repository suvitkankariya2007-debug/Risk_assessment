"""
core_engines/business_profile.py
================================
Business-unit / segment hierarchy for revenue-weighted risk quantification.

Composes with (does not replace) AssetTopologyGraph: an Asset may optionally
reference a Segment via its name. Pure arithmetic + validation only — no I/O.
"""
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from schemas.data_models import BusinessProfileResult


class BusinessUnit(BaseModel):
    """A business unit with sector/country context for threat-impact mapping."""
    model_config = ConfigDict(frozen=True, strict=True)

    name: str
    sector: str
    country: str
    employee_count: Optional[int] = None


class Segment(BaseModel):
    """A revenue-bearing segment inside a BusinessUnit."""
    model_config = ConfigDict(frozen=True, strict=True)

    name: str
    parent_business_unit: str
    revenue_pct: float = Field(ge=0.0, le=100.0)
    description: Optional[str] = None


class BusinessProfileEngine:
    """Builds a frozen BusinessProfileResult from a unit + its segments.

    Raises:
        ValueError: If segment revenue_pct values sum above 100.
    """

    def build_profile(
        self,
        business_unit: BusinessUnit,
        segments: List[Segment],
        annual_revenue_cr: float,
    ) -> BusinessProfileResult:
        if annual_revenue_cr <= 0:
            raise ValueError(
                f"annual_revenue_cr must be > 0, got {annual_revenue_cr}"
            )
        total_pct = sum(s.revenue_pct for s in segments)
        if total_pct > 100.0 + 1e-9:
            raise ValueError(
                f"Segment revenue_pct values sum to {total_pct} (> 100) — "
                "segments cannot exceed 100% of unit revenue"
            )
        for s in segments:
            if s.parent_business_unit != business_unit.name:
                raise ValueError(
                    f"Segment '{s.name}' declares parent_business_unit="
                    f"'{s.parent_business_unit}' but profile is built for "
                    f"'{business_unit.name}'"
                )
        return BusinessProfileResult(
            business_unit_name=business_unit.name,
            sector=business_unit.sector,
            country=business_unit.country,
            employee_count=business_unit.employee_count,
            segments=[s.name for s in segments],
            total_revenue_cr=round(annual_revenue_cr, 4),
        )

    def segment_revenue_cr(self, segment: Segment, annual_revenue_cr: float) -> float:
        """SegRevenue = revenue_pct/100 * business-unit annual revenue (₹ Cr)."""
        if annual_revenue_cr <= 0:
            raise ValueError(
                f"annual_revenue_cr must be > 0, got {annual_revenue_cr}"
            )
        return round(annual_revenue_cr * (segment.revenue_pct / 100.0), 4)


def build_business_profile(
    business_unit: str,
    segment_name: str,
    segment_revenue_pct: Optional[float] = None,
    sector: Optional[str] = None,
    country: Optional[str] = None,
    employee_count: Optional[int] = None,
    annual_revenue_cr: float = 100.0,
) -> BusinessProfileResult:
    """Module-level wiring shim used by api_layer/dual_routes.py.

    Builds a single-unit, single-segment profile from NLU-slot strings.
    This is a *wiring* convenience only — all validation/math lives in
    BusinessProfileEngine. If sector/country are absent we use neutral
    placeholders (they are metadata only, never used in any formula).
    """
    engine = BusinessProfileEngine()
    unit = BusinessUnit(
        name=business_unit,
        sector=sector or "Technology",
        country=country or "India",
        employee_count=int(employee_count) if employee_count is not None else None,
    )
    seg = Segment(
        name=segment_name,
        parent_business_unit=business_unit,
        revenue_pct=float(segment_revenue_pct) if segment_revenue_pct is not None else 100.0,
    )
    return engine.build_profile(unit, [seg], annual_revenue_cr)
