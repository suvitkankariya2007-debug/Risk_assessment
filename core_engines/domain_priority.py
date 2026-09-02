"""
core_engines/domain_priority.py
===============================
Security-domain prioritization ranking.

Formula (implemented EXACTLY as specified):
    D_priority = T_w * (alpha + Impact_Weight)

    T_w           : float 0-10 — how relevant the threat is to the domain.
    alpha         : normalization constant, default 1.0.
    Impact_Weight : Impact_w from segment_risk, normalized 0-1
                    (Impact_w / 100 under the 0-10 × 0-10 input scale).

Default domain list is a standard NIST-CSF-aligned set.
"""
from typing import Dict, List

from schemas.data_models import DomainPriorityResult


DEFAULT_SECURITY_DOMAINS: List[str] = [
    "Identity & Access Management",
    "Endpoint Protection",
    "Network Security",
    "Data Protection & Encryption",
    "Email & Messaging Security",
    "Cloud Security",
    "Application Security",
    "Vulnerability Management",
    "Security Monitoring & Logging",
    "Incident Response",
    "Backup & Recovery",
    "Third-Party/Vendor Risk",
    "Security Awareness & Training",
    "Governance/Risk/Compliance",
    "Physical Security",
]


class DomainPriorityEngine:
    """Ranks security domains by threat-relevance-weighted priority."""

    def __init__(self, domains: List[str] = DEFAULT_SECURITY_DOMAINS) -> None:
        self._domains = list(domains)

    def rank_domains(
        self,
        threat_domain_relevance: Dict[str, float],
        impact_w: float,
        alpha: float = 1.0,
    ) -> List[DomainPriorityResult]:
        """
        Args:
            threat_domain_relevance: mapping of domain name → T_w (0-10).
                Domains not present get T_w = 0.0.
            impact_w: raw Impact_w from segment_risk (0-100); normalized to
                0-1 internally (Impact_w / 100).
            alpha: normalization constant (default 1.0).

        Returns:
            DomainPriorityResult list sorted by D_priority descending.

        Raises:
            ValueError: If any T_w outside [0, 10], Impact_w outside [0, 100],
                or unknown domain name supplied.
        """
        if not (0.0 <= float(impact_w) <= 100.0):
            raise ValueError(f"impact_w must be in [0, 100], got {impact_w}")
        impact_weight = float(impact_w) / 100.0

        known = set(self._domains)
        for domain, t_w in threat_domain_relevance.items():
            if domain not in known:
                raise ValueError(
                    f"Unknown security domain '{domain}'. Valid domains: {sorted(known)}"
                )
            t_w = float(t_w)
            if not (0.0 <= t_w <= 10.0):
                raise ValueError(f"T_w for '{domain}' must be in [0, 10], got {t_w}")

        results: List[DomainPriorityResult] = []
        for domain in self._domains:
            t_w = float(threat_domain_relevance.get(domain, 0.0))
            # D_priority = T_w * (alpha + Impact_Weight)
            d_priority = t_w * (alpha + impact_weight)
            results.append(
                DomainPriorityResult(
                    domain=domain,
                    t_w=round(t_w, 4),
                    impact_weight=round(impact_weight, 4),
                    d_priority=round(d_priority, 4),
                )
            )

        results.sort(key=lambda r: r.d_priority, reverse=True)
        return results


def compute_domain_priorities(t_w: float, impact_w: float) -> List[DomainPriorityResult]:
    """Module-level wiring shim used by api_layer/dual_routes.py.

    The NLU layer captures a single T_w float; per the formula the same
    threat-relevance weight is applied across the full default domain set.
    Delegates straight to DomainPriorityEngine.rank_domains — no math here.
    """
    engine = DomainPriorityEngine()
    relevance = {domain: float(t_w) for domain in DEFAULT_SECURITY_DOMAINS}
    return engine.rank_domains(relevance, impact_w=impact_w)
