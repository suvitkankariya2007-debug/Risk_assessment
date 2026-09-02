"""
EPSS Exploit Prediction Engine
Grounded in Jacobs et al. (2021)

16 Elastic Net features with canonical weights.
Includes online incremental SGD learner for continuous retraining.

Phase 0d fix: when a concrete CVE id is supplied, the real per-CVE exploit
probability and percentile are fetched from the FIRST.org EPSS API
(https://api.first.org/data/v1/epss) with a hard 2-second timeout. The
offline logistic approximation below is kept strictly as a fallback for
when the API is unreachable, rate-limited, or the CVE has no live record.
"""
import json
import math
import os
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple
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


# ── Live FIRST.org EPSS API (Phase 0d) ──────────────────────────────────────
_EPSS_API_URL = "https://api.first.org/data/v1/epss"
_EPSS_TIMEOUT_SEC = 2.0
_EPSS_CACHE_TTL_SEC = 6 * 3600.0
_EPSS_CACHE: Dict[str, Tuple[float, float, float]] = {}  # cve -> (ts, prob, pct)
_executor = ThreadPoolExecutor(max_workers=2)


def _live_epss_enabled() -> bool:
    """Live API is on by default; set EPSS_DISABLE_LIVE=1 to force offline mode."""
    return os.environ.get("EPSS_DISABLE_LIVE", "").strip().lower() not in (
        "1", "true", "yes",
    )


def _fetch_live_epss(cve_id: str) -> Optional[Tuple[float, float]]:
    """
    Fetch the real (probability, percentile%) for a CVE from FIRST.org.

    Hard 2-second wall-clock cap (a slow external API must never block the
    chat response). Returns None on any failure/timeout so the caller falls
    back to the offline logistic approximation. Results are cached for 6h.
    """
    import time as _time

    key = cve_id.upper()
    now = _time.monotonic()
    cached = _EPSS_CACHE.get(key)
    if cached and (now - cached[0]) < _EPSS_CACHE_TTL_SEC:
        return (cached[1], cached[2])

    def _do_request() -> Optional[Tuple[float, float]]:
        try:
            url = f"{_EPSS_API_URL}?cve={key}"
            req = urllib.request.Request(url, headers={"User-Agent": "CyberRiskIQ/1.0"})
            with urllib.request.urlopen(req, timeout=_EPSS_TIMEOUT_SEC) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            rows = data.get("data") or []
            if not rows:
                return None
            prob = float(rows[0].get("epss", "nan"))
            # FIRST.org returns percentile as a 0-1 fraction
            pct = float(rows[0].get("percentile", "nan")) * 100.0
            if math.isnan(prob) or math.isnan(pct):
                return None
            return (prob, pct)
        except Exception:
            return None

    future = _executor.submit(_do_request)
    try:
        result = future.result(timeout=_EPSS_TIMEOUT_SEC)
    except Exception:
        return None
    if result is not None:
        _EPSS_CACHE[key] = (now, result[0], result[1])
    return result


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

        live_epss = False
        if cve_id and _live_epss_enabled():
            live = _fetch_live_epss(cve_id)
            if live is not None:
                live_prob, live_percentile = live
                if 0.0 <= live_prob <= 1.0:
                    probability = live_prob
                    percentile = live_percentile
                    live_epss = True

        return EPSSPrediction(
            cve_id=cve_id,
            epss_probability=round(probability, 6),
            percentile=round(min(percentile, 100.0), 2),
            z_score=round(z, 4),
            live_epss=live_epss,
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

