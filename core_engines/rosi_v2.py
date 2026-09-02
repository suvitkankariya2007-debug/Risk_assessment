"""
core_engines/rosi_v2.py
=======================
Cost-adjusted ROSI (v2) — extends the classic Gordon-Loeb ROSI with control
efficacy and a cost-rate adjustment.

Formula (implemented EXACTLY as specified — do not alter):
    Z_ROSI = ((ALE * ControlEfficacy) - (ControlCost * CostRate)) /
             (ControlCost * CostRate)

The original Gordon-Loeb ROSI (core_engines/rosi_optimizer.py) is retained
alongside this module — both are exposed.
"""
from schemas.data_models import ZRosiResult


class CostAdjustedROSIOptimizer:
    """Cost-adjusted Return on Security Investment evaluator."""

    def evaluate(
        self,
        ale_cr: float,
        control_efficacy_t: float,
        control_cost_cr: float,
        cost_rate: float = 1.0,
    ) -> ZRosiResult:
        """
        Args:
            ale_cr: Annualized Loss Exposure in ₹ Cr (from cia_exposure engine).
            control_efficacy_t: Realized control efficacy (from control_maturity).
            control_cost_cr: Control cost in ₹ Cr.
            cost_rate: Cost-adjustment factor (e.g. annualization factor).
                Must be > 0. Expected range: 0 < CostRate <= 1 when it
                represents the annualized share of an upfront capex;
                > 1 when it represents multi-year operating multiple.

        Raises:
            ValueError: If ALE < 0, efficacy outside [0, 1], or cost inputs <= 0.
        """
        ale_cr = float(ale_cr)
        if ale_cr < 0:
            raise ValueError(f"ale_cr must be >= 0, got {ale_cr}")
        control_efficacy_t = float(control_efficacy_t)
        if not (0.0 <= control_efficacy_t <= 1.0):
            raise ValueError(
                f"control_efficacy_t must be in [0, 1], got {control_efficacy_t}"
            )
        control_cost_cr = float(control_cost_cr)
        cost_rate = float(cost_rate)
        if control_cost_cr <= 0:
            raise ValueError(
                f"control_cost_cr must be > 0, got {control_cost_cr}"
            )
        if cost_rate <= 0:
            raise ValueError(f"cost_rate must be > 0, got {cost_rate}")

        adjusted_cost = control_cost_cr * cost_rate

        # Z_ROSI = ((ALE * ControlEfficacy) - (ControlCost * CostRate)) /
        #          (ControlCost * CostRate)
        z_rosi = ((ale_cr * control_efficacy_t) - adjusted_cost) / adjusted_cost

        return ZRosiResult(
            ale_cr=round(ale_cr, 4),
            control_efficacy_t=round(control_efficacy_t, 4),
            control_cost_cr=round(control_cost_cr, 4),
            cost_rate=round(cost_rate, 4),
            z_rosi=round(z_rosi, 4),
        )


def compute_rosi_v2(
    ale_cr: float,
    control_efficacy_t: float,
    control_cost_cr: float,
    cost_rate: float,
) -> ZRosiResult:
    """Module-level wiring shim used by api_layer/dual_routes.py.

    Delegates straight to CostAdjustedROSIOptimizer.evaluate — no math here.
    """
    return CostAdjustedROSIOptimizer().evaluate(
        ale_cr=ale_cr,
        control_efficacy_t=control_efficacy_t,
        control_cost_cr=control_cost_cr,
        cost_rate=cost_rate,
    )
