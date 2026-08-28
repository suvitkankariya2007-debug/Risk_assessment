import json
import math
import random
import time
from typing import Any, Dict, List, Optional
import numpy as np
from sklearn.linear_model import SGDClassifier
from schemas.data_models import EPSSInput, EPSSOutput


class IntrusionTelemetry:
    def __init__(self) -> None:
        self.buffer: List[Dict[str, Any]] = []

    def ingest_batch(self, size: int = 50) -> List[Dict[str, Any]]:
        vendors = ["microsoft", "ibm", "adobe", "hp", "apache", "google", "apple"]
        tags_pool = [
            "code_execution", "remote", "denial_of_service", "dos",
            "web", "memory_corruption", "local", "overflow", "injection",
        ]
        batch = []
        for _ in range(size):
            cve = f"CVE-2024-{random.randint(1000, 9999)}"
            entry = {
                "cve_id": cve,
                "vendor": random.choice(vendors),
                "reference_count": random.randint(0, 200),
                "tags": random.sample(tags_pool, k=random.randint(1, 4)),
                "exploit_poc_published": random.random() > 0.5,
                "weaponized": random.random() > 0.7,
                "label": int(random.random() > 0.4),
            }
            batch.append(entry)
            self.buffer.append(entry)
        return batch


class ContinuousRetrainingBus:
    def __init__(self) -> None:
        self.model = SGDClassifier(loss="log_loss", warm_start=True, max_iter=1000, tol=1e-3)
        self.feature_names = [
            "vend_microsoft", "vend_ibm", "vend_adobe", "vend_hp",
            "vend_apache", "vend_google", "vend_apple",
            "exp_weaponized", "exp_poc_published", "ref_count_log",
            "tag_code_execution", "tag_remote", "tag_denial_of_service",
            "tag_web", "tag_memory_corruption", "tag_local",
        ]
        self.is_fitted = False
        self.buffer: List[Dict[str, Any]] = []

    def _featurize(self, entry: Dict[str, Any]) -> np.ndarray:
        feats = np.zeros(len(self.feature_names), dtype=float)
        name_to_idx = {n: i for i, n in enumerate(self.feature_names)}
        vendor = entry.get("vendor", "")
        for known, key in {
            "microsoft": "vend_microsoft", "ibm": "vend_ibm",
            "adobe": "vend_adobe", "hp": "vend_hp",
            "apache": "vend_apache", "google": "vend_google", "apple": "vend_apple",
        }.items():
            if known in vendor.lower():
                feats[name_to_idx[key]] = 1.0
        if entry.get("weaponized"):
            feats[name_to_idx["exp_weaponized"]] = 1.0
        if entry.get("exploit_poc_published"):
            feats[name_to_idx["exp_poc_published"]] = 1.0
        rc = entry.get("reference_count", 0)
        feats[name_to_idx["ref_count_log"]] = math.log(1 + rc)
        for tag in entry.get("tags", []):
            t = tag.lower().replace(" ", "_")
            mapped = {
                "code_execution": "tag_code_execution", "remote": "tag_remote",
                "denial_of_service": "tag_denial_of_service", "dos": "tag_denial_of_service",
                "web": "tag_web", "memory_corruption": "tag_memory_corruption", "local": "tag_local",
            }.get(t)
            if mapped and mapped in name_to_idx:
                feats[name_to_idx[mapped]] = 1.0
        return feats.reshape(1, -1)

    def rolling_origin_retrain(self, batch: List[Dict[str, Any]]) -> None:
        if not batch:
            return
        X = np.vstack([self._featurize(e) for e in batch])
        y = np.array([e["label"] for e in batch])
        if not self.is_fitted:
            self.model.partial_fit(X, y, classes=[0, 1])
            self.is_fitted = True
        else:
            self.model.partial_fit(X, y)

    def get_epss_weight(self, cve_id: str) -> float:
        entry = next((e for e in self.buffer if e["cve_id"] == cve_id), None)
        if not entry:
            return 0.5
        x = self._featurize(entry)
        prob = self.model.predict_proba(x)[0]
        return float(prob[1]) if len(prob) > 1 else 0.5

    def get_buffer(self) -> List[Dict[str, Any]]:
        return list(self.buffer)

    def ingest_batch(self, size: int = 50) -> List[Dict[str, Any]]:
        vendors = ["microsoft", "ibm", "adobe", "hp", "apache", "google", "apple"]
        tags_pool = [
            "code_execution", "remote", "denial_of_service", "dos",
            "web", "memory_corruption", "local", "overflow", "injection",
        ]
        batch = []
        for _ in range(size):
            cve = f"CVE-2024-{random.randint(1000, 9999)}"
            entry = {
                "cve_id": cve,
                "vendor": random.choice(vendors),
                "reference_count": random.randint(0, 200),
                "tags": random.sample(tags_pool, k=random.randint(1, 4)),
                "exploit_poc_published": random.random() > 0.5,
                "weaponized": random.random() > 0.7,
                "label": int(random.random() > 0.4),
            }
            batch.append(entry)
            self.buffer.append(entry)
        return batch
