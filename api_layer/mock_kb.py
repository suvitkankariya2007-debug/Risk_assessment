"""
api_layer/mock_kb.py
=====================
Demo/test data for filling in vulnerability and asset details when requested.
"""
from typing import TypedDict, Dict


class VulnEntry(TypedDict):
    vendor: str
    tags: list
    exploit_weaponized: bool
    poc_published: bool
    reference_count: int
    description: str


class AssetEntry(TypedDict):
    daily_revenue_inr: float
    asset_replacement_cost_inr: float


MOCK_VULNERABILITIES: Dict[str, VulnEntry] = {
    "CVE-2024-1234": {
        "vendor": "microsoft", "tags": ["remote", "code_execution"],
        "exploit_weaponized": True, "poc_published": True, "reference_count": 340,
        "description": "A remote attacker can execute arbitrary code via a crafted request, leading to full system compromise.",
    },
    "CVE-2024-5678": {
        "vendor": "apache", "tags": ["web", "dos"],
        "exploit_weaponized": False, "poc_published": True, "reference_count": 58,
        "description": "A denial of service vulnerability in the web server module under high load.",
    },
    "CVE-2024-9012": {
        "vendor": "apple", "tags": ["local", "memory_corruption"],
        "exploit_weaponized": False, "poc_published": False, "reference_count": 4,
        "description": "A local memory corruption issue requiring physical access.",
    },
}

_DEFAULT_VULN: VulnEntry = {
    "vendor": "microsoft", "tags": ["remote", "code_execution"],
    "exploit_weaponized": True, "poc_published": True, "reference_count": 50,
    "description": "A vulnerability with active threat intelligence signals.",
}

MOCK_ASSETS: Dict[str, AssetEntry] = {
    "AST-001": {"daily_revenue_inr": 4_000_000, "asset_replacement_cost_inr": 12_000_000},
    "AST-002": {"daily_revenue_inr": 2_500_000, "asset_replacement_cost_inr": 8_000_000},
    "AST-014": {"daily_revenue_inr": 6_000_000, "asset_replacement_cost_inr": 20_000_000},
    "AST-029": {"daily_revenue_inr": 1_800_000, "asset_replacement_cost_inr": 5_500_000},
}

_DEFAULT_ASSET: AssetEntry = {"daily_revenue_inr": 2_000_000, "asset_replacement_cost_inr": 10_000_000}


def lookup_vuln(cve_id: str) -> VulnEntry:
    if not cve_id:
        return _DEFAULT_VULN
    return MOCK_VULNERABILITIES.get(cve_id.upper(), _DEFAULT_VULN)


def lookup_asset(asset_id: str) -> AssetEntry:
    if not asset_id:
        return _DEFAULT_ASSET
    return MOCK_ASSETS.get(asset_id.upper(), _DEFAULT_ASSET)
