"""
Explainable AI (XAI) Trust Auditor
Grounded in Mirtaheri et al. (2025)

Implements:
    - Weighted Cosine Similarity (WCS) against CVSS definition keywords
    - Adaptive IQR Thresholding: T_IQR = Q3 + sigma
    - Trust Formula: Trust = (alpha * S_t + beta * S_all * (1 - delta_t/delta_all)) * 100
    - Status: EXPERT_GROUNDED if trust >= 75.0% else UNALIGNED_REVIEW_REQUIRED
"""
import math
from typing import List, Dict, Tuple
from collections import Counter

import numpy as np

from schemas.data_models import XAITrustResult


# CVSS ground-truth definition keywords
CVSS_KEYWORDS: List[str] = [
    "remote", "unauthenticated", "code_execution", "heap_overflow",
    "network", "local", "adjacent", "physical",
    "low", "high", "none", "required", "unchanged", "changed",
    "confidentiality", "integrity", "availability",
    "overflow", "injection", "bypass", "escalation", "denial",
]

# Trust formula weights (Mirtaheri et al., 2025)
ALPHA = 0.6  # Weight for salient token similarity
BETA = 0.4   # Weight for all-token similarity


def _char_trigrams(text: str) -> Counter:
    """Extract character trigram frequency vector from text."""
    t = text.lower().strip()
    grams: Counter = Counter()
    for i in range(max(0, len(t) - 2)):
        grams[t[i:i + 3]] += 1
    return grams


def _cosine_similarity(a: str, b: str) -> float:
    """Compute cosine similarity between two strings using character trigrams."""
    vec_a = _char_trigrams(a)
    vec_b = _char_trigrams(b)
    if not vec_a or not vec_b:
        return 0.0

    all_keys = set(vec_a.keys()) | set(vec_b.keys())
    dot = sum(vec_a.get(k, 0) * vec_b.get(k, 0) for k in all_keys)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _best_keyword_similarity(token: str) -> float:
    """Compute max cosine similarity of a token against all CVSS keywords."""
    if not token:
        return 0.0
    return max(_cosine_similarity(token, kw) for kw in CVSS_KEYWORDS)


class XAITrustAuditor:
    """Trust-aware explainability auditor with Adaptive IQR thresholding."""

    def evaluate_trust_score(
        self, description: str, salient_tokens: List[str]
    ) -> XAITrustResult:
        """
        Evaluate model trust score against CVSS ground-truth keywords.

        Args:
            description: Full CVE description text.
            salient_tokens: Tokens identified as most influential by the model.

        Returns:
            XAITrustResult with trust score, tokens, and alignment status.
        """
        # Tokenize the full description
        desc_tokens = [w for w in description.lower().split() if len(w) > 2]

        # Compute similarities for salient tokens
        salient_sims = np.array(
            [_best_keyword_similarity(t) for t in salient_tokens]
        ) if salient_tokens else np.array([0.0])

        # Compute similarities for all description tokens
        all_sims = np.array(
            [_best_keyword_similarity(t) for t in desc_tokens]
        ) if desc_tokens else np.array([0.0])

        # Adaptive IQR Thresholding
        if len(salient_sims) > 1:
            q3 = float(np.percentile(salient_sims, 75))
            sigma = float(np.std(salient_sims))
        else:
            q3 = float(salient_sims[0]) if len(salient_sims) > 0 else 0.0
            sigma = 0.0

        iqr_threshold = q3 + sigma  # T_IQR = Q3 + sigma

        # Mirtaheri trust formula components
        s_t = float(np.mean(salient_sims))      # Mean similarity of salient tokens
        s_all = float(np.mean(all_sims))         # Mean similarity of all tokens
        delta_t = float(np.std(salient_sims))    # Std dev of salient similarities
        delta_all = float(np.std(all_sims)) if len(all_sims) > 1 else 1.0

        # Trust_model = (alpha * S_t + beta * S_all * (1 - delta_t / delta_all)) * 100
        ratio = delta_t / delta_all if delta_all > 0 else 0.0
        trust_score = (ALPHA * s_t + BETA * s_all * (1.0 - ratio)) * 100.0

        # Clamp to [0, 100]
        trust_score = max(0.0, min(100.0, trust_score))

        # Alignment status per spec: 75.0% threshold
        alignment_status = (
            "EXPERT_GROUNDED"
            if trust_score >= 75.0
            else "UNALIGNED_REVIEW_REQUIRED"
        )

        return XAITrustResult(
            trust_score_pct=round(trust_score, 2),
            salient_tokens=salient_tokens,
            alignment_status=alignment_status,
        )

    # --- Backward compatibility alias for Developer B api_layer ---

    def audit(self, inp):
        """Backward-compatible alias accepting XAIInput, returning XAIOutput."""
        from schemas.data_models import XAIOutput

        result = self.evaluate_trust_score(
            description=inp.generated_text,
            salient_tokens=inp.salient_tokens,
        )

        # Compute IQR threshold for legacy output
        sims = [_best_keyword_similarity(t) for t in inp.salient_tokens]
        arr = np.array(sims) if sims else np.array([0.0])
        q3 = float(np.percentile(arr, 75)) if len(arr) > 1 else float(arr[0])
        sigma = float(np.std(arr)) if len(arr) > 1 else 0.0
        threshold = q3 + sigma

        misaligned = [t for t, s in zip(inp.salient_tokens, sims) if s < threshold]
        flags = "EXPERT_GROUNDED" if result.trust_score_pct >= 75.0 else "UNALIGNED_REVIEW_REQUIRED"

        return XAIOutput(
            trust_score_pct=result.trust_score_pct,
            iqr_threshold=round(threshold, 4),
            flags_status=flags,
            misaligned_tokens=misaligned,
        )

