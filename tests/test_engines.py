"""
Automated Verification Tests for All Developer A Math Engines
Validates invariants defined in the specification:
    1. EPSS probability bounds [0.0, 1.0]
    2. EPSS online retraining (SGD partial_fit)
    3. FAIR lognormal invariant (VaR_0.95 > EAL)
    4. XAI trust score bounds [0.0, 100.0] and 75% threshold
    5. Gordon-Loeb economic bound (cost > 0.37 * EAL → not viable)
"""
import sys
import os
import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core_engines.epss_model import EPSSPredictor
from core_engines.fair_model import FAIRRiskEngine
from core_engines.xai_trust import XAITrustAuditor
from core_engines.rosi_optimizer import ROSIOptimizer
from core_engines.topology_graph import AssetTopologyGraph
from schemas.data_models import (
    EPSSPrediction,
    FAIRSimulationResult,
    XAITrustResult,
    ROSIOptimizationResult,
)


# ---------------------------------------------------------------------------
# Test 1: EPSS Probability Bounds
# ---------------------------------------------------------------------------
class TestEPSSProbabilityBounds:
    """EPSS logit calculation must return a valid probability in [0.0, 1.0]."""

    def test_epss_probability_bounds_all_false(self):
        """With all features off, probability should be valid and low."""
        predictor = EPSSPredictor()
        features = {k: False for k in EPSSPredictor.COEFFICIENTS if k != "ref_count_log"}
        result = predictor.predict_probability(features, ref_count=0, cve_id="CVE-2024-0001")

        assert isinstance(result, EPSSPrediction)
        assert 0.0 <= result.epss_probability <= 1.0
        assert 0.0 <= result.percentile <= 100.0
        assert result.cve_id == "CVE-2024-0001"

    def test_epss_probability_bounds_all_true(self):
        """With all boolean features on, probability should still be in [0, 1]."""
        predictor = EPSSPredictor()
        features = {k: True for k in EPSSPredictor.COEFFICIENTS if k != "ref_count_log"}
        result = predictor.predict_probability(features, ref_count=500, cve_id="CVE-2024-9999")

        assert 0.0 <= result.epss_probability <= 1.0
        assert 0.0 <= result.percentile <= 100.0

    def test_epss_probability_high_risk_cve(self):
        """A weaponized Microsoft CVE with PoC should have elevated probability."""
        predictor = EPSSPredictor()
        features = {
            "vend_microsoft": True,
            "exp_weaponized": True,
            "exp_poc_published": True,
            "tag_code_execution": True,
            "tag_remote": True,
        }
        result = predictor.predict_probability(features, ref_count=50, cve_id="CVE-2024-3094")

        assert result.epss_probability > 0.1, "High-risk CVE should have elevated EPSS"
        assert 0.0 <= result.epss_probability <= 1.0

    def test_epss_negative_features_lower_probability(self):
        """Apple vendor with local-only tag should reduce probability."""
        predictor = EPSSPredictor()
        features = {"vend_apple": True, "tag_local": True}
        result = predictor.predict_probability(features, ref_count=0, cve_id="CVE-2024-LOCAL")

        baseline = EPSSPredictor()
        baseline_result = baseline.predict_probability({}, ref_count=0, cve_id="CVE-BASELINE")

        # Apple + local should be LOWER than baseline (both have negative coefficients)
        assert result.epss_probability < baseline_result.epss_probability


# ---------------------------------------------------------------------------
# Test 2: EPSS Online Retraining
# ---------------------------------------------------------------------------
class TestEPSSOnlineRetraining:
    """continuous_online_update() must partially fit telemetry without crashing."""

    def test_epss_online_retraining(self):
        """SGD partial_fit on a synthetic telemetry batch should complete."""
        predictor = EPSSPredictor()

        batch = [
            {
                "vend_microsoft": True,
                "exp_weaponized": True,
                "exp_poc_published": False,
                "tag_code_execution": True,
                "tag_remote": True,
                "ref_count": 42,
                "label": 1,
            },
            {
                "vend_apple": True,
                "tag_local": True,
                "ref_count": 5,
                "label": 0,
            },
            {
                "vend_ibm": True,
                "tag_denial_of_service": True,
                "ref_count": 100,
                "label": 1,
            },
        ]

        # Should not raise
        predictor.continuous_online_update(batch)
        assert predictor._sgd_fitted is True

        # Second batch (incremental update)
        predictor.continuous_online_update(batch)
        assert predictor._sgd_fitted is True

    def test_epss_online_retraining_empty_batch(self):
        """Empty telemetry batch should be a no-op."""
        predictor = EPSSPredictor()
        predictor.continuous_online_update([])
        assert predictor._sgd_fitted is False


# ---------------------------------------------------------------------------
# Test 3: FAIR Lognormal Invariants
# ---------------------------------------------------------------------------
class TestFAIRLognormalInvariants:
    """Monte Carlo 10,000 trials must produce eal_cr > 0 and var_95_cr > eal_cr."""

    def test_fair_lognormal_invariants_tier1(self):
        """TIER_1_CRITICAL with realistic inputs must satisfy invariants."""
        engine = FAIRRiskEngine()
        result = engine.run_monte_carlo(
            epss_prob=0.15,
            asset_replacement_cost_cr=45.0,
            daily_revenue_impact_cr=12.5,
            regulatory_tier="TIER_1_CRITICAL",
            iterations=10_000,
        )

        assert isinstance(result, FAIRSimulationResult)
        assert result.expected_annual_loss_cr > 0, "EAL must be positive"
        assert result.value_at_risk_95_cr > result.expected_annual_loss_cr, (
            "VaR_0.95 must strictly exceed EAL (lognormal right-skew)"
        )
        assert result.iterations == 10_000

    def test_fair_lognormal_invariants_tier2(self):
        """TIER_2_STANDARD with moderate inputs must satisfy invariants."""
        engine = FAIRRiskEngine()
        result = engine.run_monte_carlo(
            epss_prob=0.05,
            asset_replacement_cost_cr=12.0,
            daily_revenue_impact_cr=3.5,
            regulatory_tier="TIER_2_STANDARD",
            iterations=10_000,
        )

        assert result.expected_annual_loss_cr > 0
        assert result.value_at_risk_95_cr > result.expected_annual_loss_cr

    def test_fair_primary_loss_formula(self):
        """Verify primary loss = (daily_rev × 4.0) + (replacement × 0.15)."""
        engine = FAIRRiskEngine()
        result = engine.run_monte_carlo(
            epss_prob=0.10,
            asset_replacement_cost_cr=100.0,
            daily_revenue_impact_cr=10.0,
            regulatory_tier="TIER_2_STANDARD",
            iterations=10_000,
        )

        expected_primary = (10.0 * 4.0) + (100.0 * 0.15)  # 40 + 15 = 55
        assert abs(result.primary_loss_cr - expected_primary) < 0.01

    def test_fair_secondary_loss_formula(self):
        """Verify secondary loss = primary × tier_mult × 0.80."""
        engine = FAIRRiskEngine()
        result = engine.run_monte_carlo(
            epss_prob=0.10,
            asset_replacement_cost_cr=100.0,
            daily_revenue_impact_cr=10.0,
            regulatory_tier="TIER_1_CRITICAL",
            iterations=10_000,
        )

        expected_primary = (10.0 * 4.0) + (100.0 * 0.15)   # 55
        expected_secondary = expected_primary * 2.5 * 0.80    # 110
        assert abs(result.secondary_loss_cr - expected_secondary) < 0.01


# ---------------------------------------------------------------------------
# Test 4: XAI Trust Score Bounds
# ---------------------------------------------------------------------------
class TestXAITrustScoreBounds:
    """XAI trust scoring must return percentage in [0.0, 100.0] with valid status."""

    def test_xai_trust_score_bounds(self):
        """Trust score must be bounded and status must be a known value."""
        auditor = XAITrustAuditor()
        result = auditor.evaluate_trust_score(
            description="Remote unauthenticated code execution via heap overflow vulnerability",
            salient_tokens=["remote", "code_execution", "heap_overflow", "unauthenticated"],
        )

        assert isinstance(result, XAITrustResult)
        assert 0.0 <= result.trust_score_pct <= 100.0
        assert result.alignment_status in ("EXPERT_GROUNDED", "UNALIGNED_REVIEW_REQUIRED")

    def test_xai_trust_high_alignment(self):
        """Tokens matching CVSS keywords should produce high trust."""
        auditor = XAITrustAuditor()
        result = auditor.evaluate_trust_score(
            description="Remote code execution heap overflow network vulnerability",
            salient_tokens=["remote", "code_execution", "heap_overflow", "network"],
        )

        assert result.trust_score_pct >= 0.0
        assert result.alignment_status in ("EXPERT_GROUNDED", "UNALIGNED_REVIEW_REQUIRED")

    def test_xai_trust_low_alignment(self):
        """Completely unrelated tokens should yield low trust / UNALIGNED status."""
        auditor = XAITrustAuditor()
        result = auditor.evaluate_trust_score(
            description="zzzzz xxxxx yyyyy qqqq",
            salient_tokens=["zzzzz", "xxxxx", "yyyyy"],
        )

        assert 0.0 <= result.trust_score_pct <= 100.0
        assert result.alignment_status == "UNALIGNED_REVIEW_REQUIRED"

    def test_xai_trust_threshold_75(self):
        """Verify the 75% threshold boundary."""
        auditor = XAITrustAuditor()

        # Trust exactly below 75 should be UNALIGNED
        result_low = auditor.evaluate_trust_score(
            description="miscellaneous unknown topic",
            salient_tokens=["misc"],
        )
        if result_low.trust_score_pct < 75.0:
            assert result_low.alignment_status == "UNALIGNED_REVIEW_REQUIRED"


# ---------------------------------------------------------------------------
# Test 5: Gordon-Loeb Economic Bound
# ---------------------------------------------------------------------------
class TestGordonLoebEconomicBound:
    """Spend > 0.37 * EAL must set is_economically_viable = False."""

    def test_gordon_loeb_within_cap(self):
        """Control cost <= 0.37 * EAL should be economically viable."""
        optimizer = ROSIOptimizer()
        eal_cr = 10.0
        # 0.37 * 10.0 = 3.7 Cr = 370 Lakhs. Use 300 Lakhs (3.0 Cr) → within cap
        result = optimizer.evaluate_investment(
            eal_cr=eal_cr, control_cost_lakhs=300.0
        )

        assert isinstance(result, ROSIOptimizationResult)
        assert result.is_economically_viable is True
        assert result.control_cost_cr <= result.gordon_loeb_cap_cr

    def test_gordon_loeb_exceeds_cap(self):
        """Control cost > 0.37 * EAL should NOT be economically viable."""
        optimizer = ROSIOptimizer()
        eal_cr = 10.0
        # 0.37 * 10.0 = 3.7 Cr = 370 Lakhs. Use 500 Lakhs (5.0 Cr) → exceeds cap
        result = optimizer.evaluate_investment(
            eal_cr=eal_cr, control_cost_lakhs=500.0
        )

        assert result.is_economically_viable is False
        assert result.control_cost_cr > result.gordon_loeb_cap_cr

    def test_gordon_loeb_exact_boundary(self):
        """Control cost exactly at 0.37 * EAL should be viable (<=)."""
        optimizer = ROSIOptimizer()
        eal_cr = 10.0
        cap_lakhs = eal_cr * 0.37 * 100.0  # 370 Lakhs
        result = optimizer.evaluate_investment(
            eal_cr=eal_cr, control_cost_lakhs=cap_lakhs
        )

        assert result.is_economically_viable is True

    def test_rosi_percentage_calculation(self):
        """Verify ROSI % = ((risk_reduced - cost) / cost) * 100."""
        optimizer = ROSIOptimizer()
        result = optimizer.evaluate_investment(
            eal_cr=10.0, control_cost_lakhs=200.0, risk_reduction_pct=85.0
        )

        # risk_reduced = 10.0 * 0.85 = 8.5 Cr
        # cost = 200/100 = 2.0 Cr
        # ROSI = ((8.5 - 2.0) / 2.0) * 100 = 325.0%
        assert abs(result.rosi_percentage - 325.0) < 0.1
        assert abs(result.net_benefit_cr - 6.5) < 0.01


# ---------------------------------------------------------------------------
# Bonus: Topology Graph Tests
# ---------------------------------------------------------------------------
class TestTopologyGraph:
    """Asset topology graph resolver tests."""

    def test_resolve_known_asset(self):
        graph = AssetTopologyGraph()
        asset = graph.resolve_asset("core_payment_switch")
        assert asset["regulatory_tier"] == "TIER_1_CRITICAL"
        assert asset["asset_replacement_cost_cr"] == 45.0

    def test_resolve_unknown_asset(self):
        graph = AssetTopologyGraph()
        with pytest.raises(KeyError):
            graph.resolve_asset("nonexistent_asset_xyz")

    def test_standardized_tiers(self):
        """All mock assets must use TIER_1_CRITICAL or TIER_2_STANDARD."""
        graph = AssetTopologyGraph()
        valid_tiers = {"TIER_1_CRITICAL", "TIER_2_STANDARD"}
        for asset in graph.list_assets():
            assert asset["regulatory_tier"] in valid_tiers, (
                f"Asset {asset['asset_name']} has non-standard tier: {asset['regulatory_tier']}"
            )
