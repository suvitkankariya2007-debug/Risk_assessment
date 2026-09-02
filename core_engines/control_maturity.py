"""
core_engines/control_maturity.py
================================
Control-maturity multipliers and control-efficacy computation.

Six fixed multipliers (exact values, do not alter):
    Not Implemented = 1.25    Initial = 0.65     Repeatable = 0.55
    Defined         = 0.45    Managed = 0.31     Optimized = 0.25

Formula:
    ControlEfficacy_T = Efficacy_T * (1.25 - MaturityLevel)
"""
from typing import Dict

from schemas.data_models import ControlMaturityResult


class ControlMaturityEngine:
    """Maps a control's maturity level to its realized efficacy."""

    MATURITY_MULTIPLIERS: Dict[str, float] = {
        "not_implemented": 1.25,
        "initial": 0.65,
        "repeatable": 0.55,
        "defined": 0.45,
        "managed": 0.31,
        "optimized": 0.25,
    }

    def get_multiplier(self, maturity_level: str) -> float:
        key = maturity_level.strip().lower().replace(" ", "_").replace("-", "_")
        if key not in self.MATURITY_MULTIPLIERS:
            valid = ", ".join(self.MATURITY_MULTIPLIERS)
            raise ValueError(
                f"Unknown control_maturity '{maturity_level}'. Valid levels: {valid}"
            )
        return self.MATURITY_MULTIPLIERS[key]

    def evaluate(self, efficacy_t: float, maturity_level: str) -> ControlMaturityResult:
        """
        Args:
            efficacy_t: The control's nominal/promised efficacy against the
                threat, float 0-1.
            maturity_level: One of the six enum levels above.

        Raises:
            ValueError: If efficacy_t outside [0, 1] or unknown maturity level.
        """
        efficacy_t = float(efficacy_t)
        if not (0.0 <= efficacy_t <= 1.0):
            raise ValueError(f"efficacy_t must be in [0, 1], got {efficacy_t}")

        multiplier = self.get_multiplier(maturity_level)

        # ControlEfficacy_T = Efficacy_T * (1.25 - MaturityLevel)
        control_efficacy_t = efficacy_t * (1.25 - multiplier)

        # Invariant: realized efficacy can never exceed the nominal ceiling 1.25
        assert 0.0 <= control_efficacy_t <= 1.25, (
            f"ControlEfficacy_T {control_efficacy_t} outside [0, 1.25]"
        )

        return ControlMaturityResult(
            maturity_level=maturity_level.strip().lower().replace(" ", "_"),
            maturity_multiplier=multiplier,
            efficacy_t=round(efficacy_t, 4),
            control_efficacy_t=round(control_efficacy_t, 4),
        )


def evaluate_control_maturity(maturity_level: str, efficacy_t: float) -> ControlMaturityResult:
    """Module-level wiring shim used by api_layer/dual_routes.py.

    Delegates straight to ControlMaturityEngine.evaluate — no math here.
    """
    return ControlMaturityEngine().evaluate(efficacy_t=efficacy_t, maturity_level=maturity_level)
