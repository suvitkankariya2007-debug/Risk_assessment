"""
Mock Neo4j Asset Criticality & Dependency Resolver
Provides replacement cost (₹ Cr), daily revenue impact (₹ Cr),
and upstream/downstream dependency weights.
"""
from typing import Dict, List


class AssetTopologyGraph:
    """Resolves mock asset topology data with standardized tier labels."""

    MOCK_ASSETS: Dict[str, Dict] = {
        "core_payment_switch": {
            "asset_name": "Core Payment Switch",
            "asset_replacement_cost_cr": 45.0,
            "daily_revenue_impact_cr": 12.5,
            "regulatory_tier": "TIER_1_CRITICAL",
            "criticality_score": 9.8,
            "upstream_dependencies": ["api_gateway", "load_balancer"],
            "downstream_dependencies": ["settlement_engine", "ledger_db"],
        },
        "customer_db": {
            "asset_name": "Customer Database",
            "asset_replacement_cost_cr": 28.0,
            "daily_revenue_impact_cr": 8.0,
            "regulatory_tier": "TIER_1_CRITICAL",
            "criticality_score": 9.2,
            "upstream_dependencies": ["api_gateway"],
            "downstream_dependencies": ["analytics_pipeline"],
        },
        "api_gateway": {
            "asset_name": "API Gateway",
            "asset_replacement_cost_cr": 12.0,
            "daily_revenue_impact_cr": 3.5,
            "regulatory_tier": "TIER_2_STANDARD",
            "criticality_score": 8.5,
            "upstream_dependencies": [],
            "downstream_dependencies": ["core_payment_switch", "customer_db"],
        },
    }

    def resolve_asset(self, asset_name: str) -> Dict:
        """Resolve asset by name, returning cost, revenue, tier, and dependencies."""
        key = asset_name.lower().replace(" ", "_")
        if key in self.MOCK_ASSETS:
            return dict(self.MOCK_ASSETS[key])

        # Fuzzy substring search fallback
        for k, v in self.MOCK_ASSETS.items():
            if key in k or key in v["asset_name"].lower():
                return dict(v)

        raise KeyError(f"Asset '{asset_name}' not found in topology graph")

    def list_assets(self) -> List[Dict]:
        """Return all mock assets."""
        return [dict(v) for v in self.MOCK_ASSETS.values()]

    def get_dependency_weight(self, asset_name: str) -> float:
        """Compute a normalized dependency weight for blast-radius estimation."""
        try:
            asset = self.resolve_asset(asset_name)
        except KeyError:
            return 0.0
        upstream = len(asset.get("upstream_dependencies", []))
        downstream = len(asset.get("downstream_dependencies", []))
        return (upstream + downstream) / max(1, len(self.MOCK_ASSETS))

    # --- Backward compatibility aliases for Developer B api_layer ---

    def resolve(self, asset_target: str):
        """Backward-compatible alias returning an AssetNode for api_layer."""
        from schemas.data_models import AssetNode
        key = asset_target.lower().replace(" ", "_")
        data = None
        if key in self.MOCK_ASSETS:
            data = self.MOCK_ASSETS[key]
        else:
            for k, v in self.MOCK_ASSETS.items():
                if key in k or key in v["asset_name"].lower():
                    data = v
                    break
        if data is None:
            return None
        return AssetNode(
            asset_id=key.upper()[:3] + "-001",
            name=data["asset_name"],
            criticality_score=data.get("criticality_score", 5.0),
            hardware_replacement_cost_inr_cr=data["asset_replacement_cost_cr"],
            daily_revenue_impact_inr_cr=data["daily_revenue_impact_cr"],
            regulatory_tier=data["regulatory_tier"],
            asset_type="infrastructure",
        )

    def search(self, query: str) -> list:
        """Backward-compatible search returning list of AssetNode."""
        from schemas.data_models import AssetNode
        q = query.lower()
        results = []
        for k, v in self.MOCK_ASSETS.items():
            if q in v["asset_name"].lower() or q in k:
                results.append(AssetNode(
                    asset_id=k.upper()[:3] + "-001",
                    name=v["asset_name"],
                    criticality_score=v.get("criticality_score", 5.0),
                    hardware_replacement_cost_inr_cr=v["asset_replacement_cost_cr"],
                    daily_revenue_impact_inr_cr=v["daily_revenue_impact_cr"],
                    regulatory_tier=v["regulatory_tier"],
                    asset_type="infrastructure",
                ))
        return results

