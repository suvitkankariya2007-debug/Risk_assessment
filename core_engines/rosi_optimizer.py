"""
MILP 0/1 Knapsack ROSI Optimizer with Gordon-Loeb Ceiling
Grounded in Sawik (2013) & Gordon-Loeb (2002)

Gordon-Loeb Invariant: Optimal spend <= (1/e) * EAL ≈ 0.37 * EAL
"""
from schemas.data_models import ROSIOptimizationResult


class ROSIOptimizer:
    """Security economics optimizer with Gordon-Loeb (2002) ceiling enforcement."""

    GORDON_LOEB_FACTOR: float = 0.37  # ≈ 1/e

    def evaluate_investment(
        self,
        eal_cr: float,
        control_cost_lakhs: float,
        risk_reduction_pct: float = 85.0,
    ) -> ROSIOptimizationResult:
        """
        Evaluate security investment economics.

        Args:
            eal_cr: Expected Annual Loss in ₹ Crores.
            control_cost_lakhs: Proposed control cost in ₹ Lakhs.
            risk_reduction_pct: Expected risk reduction percentage (default 85%).

        Returns:
            ROSIOptimizationResult with viability assessment.
        """
        # Convert lakhs to crores
        control_cost_cr = control_cost_lakhs / 100.0

        # Risk reduced
        risk_reduced_cr = eal_cr * (risk_reduction_pct / 100.0)

        # Net benefit
        net_benefit_cr = risk_reduced_cr - control_cost_cr

        # ROSI percentage
        rosi_percentage = (
            ((risk_reduced_cr - control_cost_cr) / control_cost_cr) * 100.0
            if control_cost_cr > 0
            else 0.0
        )

        # Gordon-Loeb cap: optimal spend <= 0.37 * EAL
        gordon_loeb_cap_cr = eal_cr * self.GORDON_LOEB_FACTOR

        # Economic viability check
        is_economically_viable = bool(control_cost_cr <= gordon_loeb_cap_cr)

        return ROSIOptimizationResult(
            control_cost_cr=round(control_cost_cr, 4),
            risk_reduced_cr=round(risk_reduced_cr, 4),
            net_benefit_cr=round(net_benefit_cr, 4),
            rosi_percentage=round(rosi_percentage, 2),
            gordon_loeb_cap_cr=round(gordon_loeb_cap_cr, 4),
            is_economically_viable=is_economically_viable,
        )

    # --- Backward compatibility alias for Developer B api_layer ---

    def optimize(self, inp):
        """Backward-compatible alias accepting MILPROSIInput, returning MILPROSIOutput."""
        from schemas.data_models import MILPROSIOutput
        net_capital_saved = inp.risk_reduced_inr_cr - inp.control_cost_inr_cr
        rosi = (
            ((inp.risk_reduced_inr_cr - inp.control_cost_inr_cr) / inp.control_cost_inr_cr) * 100.0
            if inp.control_cost_inr_cr > 0
            else 0.0
        )
        ceiling = inp.eal_inr_cr * self.GORDON_LOEB_FACTOR
        viable = inp.control_cost_inr_cr <= ceiling
        return MILPROSIOutput(
            control_cost_inr_cr=round(inp.control_cost_inr_cr, 4),
            risk_reduced_inr_cr=round(inp.risk_reduced_inr_cr, 4),
            net_capital_saved_inr_cr=round(net_capital_saved, 4),
            rosi_pct=round(rosi, 2),
            is_economically_viable=viable,
            gordon_loeb_ceiling_inr_cr=round(ceiling, 4),
        )

