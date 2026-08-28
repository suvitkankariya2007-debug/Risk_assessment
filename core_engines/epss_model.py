"""
EPSS Exploit Prediction Engine
Grounded in Jacobs et al. (2021)

16 Elastic Net features with canonical weights.
Includes online incremental SGD learner for continuous retraining.
"""
import math
from typing import Dict, List

import numpy as np
from scipy import stats
from sklearn.linear_model import SGDClassifier

from schemas.data_models import EPSSPrediction


class EPSSPredictor:
    """Predictive exploit probability engine with online learning capability."""

    INTERCEPT: float = -6.18

    COEFFICIENTS: Dict[str, float] = {
        "vend_microsoft": 2.44,
        "vend_ibm": 2.07,
        "exp_weaponized": 2.00,
        "vend_adobe": 1.91,
        "vend_hp": 1.62,
        "exp_poc_published": 1.50,
        "vend_apache": 1.10,
        "ref_count_log": 1.01,
        "tag_code_execution": 0.57,
        "tag_remote": 0.23,
        "tag_denial_of_service": 0.22,
        "tag_web": 0.06,
        "tag_memory_corruption": -0.20,
        "tag_local": -0.63,
        "vend_google": -0.89,
        "vend_apple": -1.92,
    }

    FEATURE_NAMES: List[str] = list(COEFFICIENTS.keys())

    def __init__(self) -> None:
        self._sgd = SGDClassifier(
            loss="log_loss", warm_start=True, max_iter=1000, tol=1e-3
        )
        self._sgd_fitted: bool = False

    def predict_probability(
        self, features: Dict[str, bool], ref_count: int, cve_id: str = ""
    ) -> EPSSPrediction:
        """
        Compute EPSS exploit probability using the 16-feature logistic model.

        Args:
            features: Dict of boolean flags keyed by canonical feature names.
            ref_count: Number of references for this CVE.
            cve_id: Optional CVE identifier string.

        Returns:
            EPSSPrediction with probability and percentile.

        Raises:
            ValueError: If computed probability is outside [0.0, 1.0].
        """
        z = self.INTERCEPT
        for feat_name, coeff in self.COEFFICIENTS.items():
            if feat_name == "ref_count_log":
                z += coeff * math.log(1 + ref_count)
            elif features.get(feat_name, False):
                z += coeff

        probability = 1.0 / (1.0 + math.exp(-z))

        if probability < 0.0 or probability > 1.0:
            raise ValueError(
                f"EPSS probability {probability} outside valid range [0.0, 1.0]"
            )

        # Approximate percentile: where this CVE's z-score falls in the
        # population distribution. Assumes population z ~ N(INTERCEPT, sigma=2.5).
        percentile = float(
            stats.norm.cdf(z, loc=self.INTERCEPT, scale=2.5) * 100.0
        )

        return EPSSPrediction(
            cve_id=cve_id,
            epss_probability=round(probability, 6),
            percentile=round(min(percentile, 100.0), 2),
        )

    def continuous_online_update(self, telemetry_batch: List[Dict]) -> None:
        """
        Incremental partial-fit on live intrusion detection stream data
        using SGDClassifier with warm_start=True.

        Each entry in telemetry_batch must contain:
            - Feature boolean flags keyed by canonical names
            - 'ref_count': int
            - 'label': int (0 or 1, ground truth exploit outcome)
        """
        if not telemetry_batch:
            return

        X = np.zeros((len(telemetry_batch), len(self.FEATURE_NAMES)))
        y = np.zeros(len(telemetry_batch), dtype=int)

        for i, entry in enumerate(telemetry_batch):
            for j, feat_name in enumerate(self.FEATURE_NAMES):
                if feat_name == "ref_count_log":
                    X[i, j] = math.log(1 + entry.get("ref_count", 0))
                else:
                    X[i, j] = 1.0 if entry.get(feat_name, False) else 0.0
            y[i] = int(entry.get("label", 0))

        if not self._sgd_fitted:
            self._sgd.partial_fit(X, y, classes=[0, 1])
            self._sgd_fitted = True
        else:
            self._sgd.partial_fit(X, y)

    # --- Backward compatibility alias for Developer B api_layer ---

    def predict(self, inp):
        """Backward-compatible alias accepting EPSSInput, returning EPSSOutput."""
        from schemas.data_models import EPSSOutput
        vendor_map = {
            "microsoft": "vend_microsoft", "ibm": "vend_ibm",
            "adobe": "vend_adobe", "hp": "vend_hp", "apache": "vend_apache",
            "google": "vend_google", "apple": "vend_apple",
        }
        tag_map = {
            "code_execution": "tag_code_execution", "remote": "tag_remote",
            "denial_of_service": "tag_denial_of_service", "dos": "tag_denial_of_service",
            "web": "tag_web", "memory_corruption": "tag_memory_corruption", "local": "tag_local",
        }
        features = {}
        if inp.vendor:
            for known, key in vendor_map.items():
                if known in inp.vendor.lower():
                    features[key] = True
                    break
        if getattr(inp, "exploit_poc_published", False):
            features["exp_poc_published"] = True
        if getattr(inp, "weaponized", False):
            features["exp_weaponized"] = True
        for tag in getattr(inp, "tags", []):
            t = tag.lower().replace(" ", "_")
            mapped = tag_map.get(t)
            if mapped:
                features[mapped] = True

        z = self.INTERCEPT
        contrib = {}
        for feat_name, coeff in self.COEFFICIENTS.items():
            if feat_name == "ref_count_log":
                val = coeff * math.log(1 + getattr(inp, "reference_count", 0))
                z += val
                if val != 0:
                    contrib[feat_name] = val
            elif features.get(feat_name, False):
                z += coeff
                contrib[feat_name] = coeff
        p_exploit = 1.0 / (1.0 + math.exp(-z))
        return EPSSOutput(
            cve_id=inp.cve_id,
            z_score=z,
            p_exploit=round(p_exploit, 6),
            feature_contributions=contrib,
        )

