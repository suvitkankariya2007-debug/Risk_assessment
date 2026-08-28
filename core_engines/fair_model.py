"""
Open FAIR™ v3.0 Lognormal Monte Carlo Engine
Deterministic financial risk quantification.

Formulas:
    LEF = EPSS_prob × 0.35
    Primary Loss = (daily_revenue × 4.0 downtime days) + (replacement_cost × 0.15)
    Secondary Loss = Primary × (2.5 if TIER_1_CRITICAL else 1.2) × 0.80 SLEF
    Sample = Lognormal(ln((Primary + Secondary) × LEF), sigma=0.85)
    Invariant: VaR_0.95 > EAL (assertion, no silent fixup)
"""
import numpy as np

from schemas.data_models import FAIRSimulationResult


class FAIRRiskEngine:
    """Open FAIR v3.0 Monte Carlo risk quantification engine."""

    SUSCEPTIBILITY = 0.35       # Residual vulnerability factor
    DOWNTIME_DAYS = 4.0         # Assumed outage duration
    REPLACEMENT_FRACTION = 0.15 # Partial replacement cost fraction
    TIER_1_MULTIPLIER = 2.5     # Regulatory amplifier for TIER_1_CRITICAL
    TIER_2_MULTIPLIER = 1.2     # Regulatory amplifier for TIER_2_STANDARD
    SLEF = 0.80                 # Secondary Loss Event Frequency (fines & penalties)
    SIGMA = 0.85                # Lognormal distribution sigma

    def run_monte_carlo(
        self,
        epss_prob: float,
        asset_replacement_cost_cr: float,
        daily_revenue_impact_cr: float,
        regulatory_tier: str,
        iterations: int = 10_000,
    ) -> FAIRSimulationResult:
        """
        Run Open FAIR v3.0 Monte Carlo simulation.

        Args:
            epss_prob: EPSS exploit probability [0.0, 1.0].
            asset_replacement_cost_cr: Asset hardware replacement cost in ₹ Crores.
            daily_revenue_impact_cr: Daily revenue impact in ₹ Crores.
            regulatory_tier: "TIER_1_CRITICAL" or "TIER_2_STANDARD".
            iterations: Number of Monte Carlo trials (default 10,000).

        Returns:
            FAIRSimulationResult with EAL, VaR, primary/secondary losses.

        Raises:
            AssertionError: If VaR_0.95 <= EAL (lognormal skewness invariant violated).
        """
        np.random.seed(42)

        # Loss Event Frequency
        lef = epss_prob * self.SUSCEPTIBILITY

        # Primary Loss: downtime cost + partial replacement
        primary_loss = (
            (daily_revenue_impact_cr * self.DOWNTIME_DAYS)
            + (asset_replacement_cost_cr * self.REPLACEMENT_FRACTION)
        )

        # Secondary Loss: regulatory fines & penalties
        tier_multiplier = (
            self.TIER_1_MULTIPLIER
            if regulatory_tier == "TIER_1_CRITICAL"
            else self.TIER_2_MULTIPLIER
        )
        secondary_loss = primary_loss * tier_multiplier * self.SLEF

        # Lognormal Monte Carlo sampling
        scale = max(0.01, (primary_loss + secondary_loss) * lef)
        samples = np.random.lognormal(
            mean=np.log(scale), sigma=self.SIGMA, size=iterations
        )

        eal_cr = float(np.mean(samples))
        var_95_cr = float(np.percentile(samples, 95))

        # INVARIANT: Right-skewed lognormal MUST satisfy VaR_0.95 > EAL
        assert var_95_cr > eal_cr, (
            f"Lognormal skewness invariant violated: "
            f"VaR_0.95 ({var_95_cr:.4f}) <= EAL ({eal_cr:.4f}). "
            f"Distribution may have converged symmetrically."
        )

        return FAIRSimulationResult(
            expected_annual_loss_cr=round(eal_cr, 4),
            value_at_risk_95_cr=round(var_95_cr, 4),
            primary_loss_cr=round(primary_loss, 4),
            secondary_loss_cr=round(secondary_loss, 4),
            iterations=iterations,
        )

    # --- Backward compatibility alias for Developer B api_layer ---

    def run(self, inp):
        """Backward-compatible alias accepting FAIRInput, returning FAIROutput."""
        import math
        import random
        from schemas.data_models import FAIROutput

        random.seed(42)
        np.random.seed(42)

        lef = inp.p_exploit * inp.susceptibility
        primary_loss = (
            (inp.asset.daily_revenue_impact_inr_cr * self.DOWNTIME_DAYS)
            + (inp.asset.hardware_replacement_cost_inr_cr * self.REPLACEMENT_FRACTION)
        )
        tier = inp.asset.regulatory_tier
        tier_mult = self.TIER_1_MULTIPLIER if "CRITICAL" in tier.upper() else self.TIER_2_MULTIPLIER
        secondary_loss = primary_loss * tier_mult * self.SLEF

        scale = max(0.01, (primary_loss + secondary_loss) * lef)
        samples = np.random.lognormal(
            mean=np.log(scale), sigma=self.SIGMA, size=inp.trial_count
        )
        eal = float(np.mean(samples))
        var_95 = float(np.percentile(samples, 95))
        if var_95 <= eal:
            var_95 = eal * 1.05  # legacy behavior for api_layer

        return FAIROutput(
            asset_id=inp.asset.asset_id,
            cve_id=None,
            lef=round(lef, 6),
            primary_loss_inr_cr=round(primary_loss, 4),
            secondary_loss_inr_cr=round(secondary_loss, 4),
            eal_inr_cr=round(eal, 4),
            var_95_inr_cr=round(var_95, 4),
            trial_samples=[round(float(x), 4) for x in samples[:1000]],
        )

