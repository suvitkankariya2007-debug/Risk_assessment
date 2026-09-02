import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core_engines.business_profile import BusinessProfileEngine, BusinessUnit, Segment
from core_engines.segment_risk import SegmentRiskEngine
from core_engines.control_maturity import ControlMaturityEngine
from schemas.data_models import BusinessProfileResult, SegmentRiskResult, ControlMaturityResult

class TestBusinessProfileEngine:
    def test_build_profile(self):
        engine = BusinessProfileEngine()
        unit = BusinessUnit(name="Retail Banking", sector="Finance", country="India", employee_count=1000)
        seg1 = Segment(name="Credit Cards", parent_business_unit="Retail Banking", revenue_pct=40.0)
        seg2 = Segment(name="Mortgages", parent_business_unit="Retail Banking", revenue_pct=60.0)

        result = engine.build_profile(unit, [seg1, seg2], annual_revenue_cr=500.0)
        assert isinstance(result, BusinessProfileResult)
        assert result.total_revenue_cr == 500.0
        assert result.business_unit_name == "Retail Banking"
        assert len(result.segments) == 2

    def test_segment_revenue_cr(self):
        engine = BusinessProfileEngine()
        seg = Segment(name="Credit Cards", parent_business_unit="Retail Banking", revenue_pct=40.0)
        seg_rev = engine.segment_revenue_cr(seg, annual_revenue_cr=500.0)
        assert seg_rev == 200.0  # 40% of 500

    def test_invalid_revenue_pct_sum(self):
        engine = BusinessProfileEngine()
        unit = BusinessUnit(name="Retail Banking", sector="Finance", country="India")
        seg1 = Segment(name="Cards", parent_business_unit="Retail Banking", revenue_pct=60.0)
        seg2 = Segment(name="Loans", parent_business_unit="Retail Banking", revenue_pct=50.0)
        
        with pytest.raises(ValueError, match="Segment revenue_pct values sum to 110.0"):
            engine.build_profile(unit, [seg1, seg2], annual_revenue_cr=500.0)

class TestSegmentRiskEngine:
    def test_segment_risk_evaluation(self):
        engine = SegmentRiskEngine()
        # impact_operational=8.0, impact_financial=5.0 -> impact_w = 40.0
        # seg_revenue_cr = 100.0 -> seg_impact_cr = 100.0 * 40.0 = 4000.0
        # risk_w = 2.0 -> risk_weighting_factor = 40.0 * 2.0 = 80.0
        # seg_risk_cr = 4000.0 * 80.0 = 320000.0
        result = engine.evaluate(
            seg_revenue_cr=100.0,
            impact_operational=8.0,
            impact_financial=5.0,
            risk_w=2.0
        )
        assert isinstance(result, SegmentRiskResult)
        assert result.impact_w == 40.0
        assert result.seg_impact_cr == 4000.0
        assert result.risk_weighting_factor == 80.0
        assert result.seg_risk_cr == 320000.0

    def test_invalid_inputs(self):
        engine = SegmentRiskEngine()
        with pytest.raises(ValueError, match="must be in \\[0, 10\\]"):
            engine.evaluate(seg_revenue_cr=100.0, impact_operational=11.0, impact_financial=5.0, risk_w=2.0)

class TestControlMaturityEngine:
    def test_control_maturity_evaluation(self):
        engine = ControlMaturityEngine()
        # efficacy_t = 0.8
        # maturity_level = 'optimized' -> multiplier = 0.25
        # control_efficacy_t = 0.8 * (1.25 - 0.25) = 0.8 * 1.0 = 0.8
        result = engine.evaluate(efficacy_t=0.8, maturity_level="optimized")
        assert isinstance(result, ControlMaturityResult)
        assert result.maturity_multiplier == 0.25
        assert result.control_efficacy_t == 0.8

    def test_invalid_maturity_level(self):
        engine = ControlMaturityEngine()
        with pytest.raises(ValueError, match="Unknown control_maturity"):
            engine.evaluate(efficacy_t=0.8, maturity_level="unknown_level")
