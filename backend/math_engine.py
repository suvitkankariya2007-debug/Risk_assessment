from __future__ import annotations

import math
from typing import Iterable

import numpy as np

from backend.data import ACTIVE_ATTACK_STATE, BASELINE_BU_EAL_LAKHS, BASELINE_EAL_LAKHS, DIGITAL_ASSETS, MITIGATION_ACTIONS, MITIGATION_CATALOG
from backend.schemas import MonteCarloResponse, OptimizerResponse, ScenarioResponse


def _get_asset(asset_id: str | int):
    if asset_id is None:
        raise ValueError("Asset identifier is required.")

    identifier = str(asset_id).strip()
    if not identifier:
        raise ValueError("Asset identifier cannot be empty.")

    try:
        asset_key = int(identifier)
    except (TypeError, ValueError):
        asset_key = None

    if asset_key is not None:
        for asset in DIGITAL_ASSETS:
            if int(asset["id"]) == asset_key:
                return asset
    else:
        for asset in DIGITAL_ASSETS:
            if str(asset["name"]).lower() == identifier.lower():
                return asset

    raise ValueError(f"Asset with id or name '{asset_id}' was not found.")


def _normalize_action_id(value: str | int) -> int:
    try:
        action_id = int(value)
        return action_id
    except (TypeError, ValueError):
        pass

    normalized = str(value).strip().lower()
    for action in MITIGATION_ACTIONS:
        if normalized in {str(action["id"]), action["name"].strip().lower()}:
            return int(action["id"])

    raise ValueError(f"Mitigation action '{value}' was not found.")


def compute_monte_carlo(asset_id: str, trials: int = 50000) -> MonteCarloResponse:
    """Simulate a compound Poisson-triangular loss distribution for a given asset."""
    if trials <= 0:
        raise ValueError("trials must be a positive integer")

    asset = _get_asset(asset_id)
    loss_params = asset["loss_params"]
    rate = float(loss_params["lambda"])
    annual_loss_reference = float(asset["baseline_eal_lakhs"])
    if ACTIVE_ATTACK_STATE.get("is_attack_active"):
        target = str(ACTIVE_ATTACK_STATE.get("target_asset") or "")
        if target and (str(asset.get("name", "")).lower() == target.lower() or str(asset.get("id", "")).lower() == target.lower()):
            annual_loss_reference += float(ACTIVE_ATTACK_STATE.get("eal_spike_cr", 0.0)) * 100.0
    fair_cam = asset.get("fair_cam", {"threat_resistance_pct": 0, "loss_mitigation_pct": 0})
    threat_resistance = float(fair_cam.get("threat_resistance_pct", 0.0)) / 100.0
    loss_mitigation = float(fair_cam.get("loss_mitigation_pct", 0.0)) / 100.0

    adjusted_rate = max(rate * (1.0 - threat_resistance), 0.02)
    if ACTIVE_ATTACK_STATE.get("is_attack_active") and str(ACTIVE_ATTACK_STATE.get("target_asset") or "").lower() in {str(asset.get("name", "")).lower(), str(asset.get("id", "")).lower()}:
        adjusted_rate *= 1.8
    effective_loss_scale = annual_loss_reference / max(adjusted_rate * 1.5, 1e-6)
    effective_loss_scale *= max(1.0 - loss_mitigation, 0.2)

    rng = np.random.default_rng(seed=42 + int(asset["id"]))
    event_counts = rng.poisson(adjusted_rate, size=int(trials))
    annual_losses = np.zeros(int(trials), dtype=float)

    for idx, event_count in enumerate(event_counts):
        if event_count == 0:
            continue
        event_losses = rng.triangular(
            left=0.5 * effective_loss_scale,
            mode=1.0 * effective_loss_scale,
            right=2.8 * effective_loss_scale,
            size=int(event_count),
        )
        annual_losses[idx] = float(event_losses.sum())

    mean_loss = float(annual_losses.mean())
    p95_loss = float(np.quantile(annual_losses, 0.95))
    p99_loss = float(np.quantile(annual_losses, 0.99))

    hist_counts, _ = np.histogram(annual_losses, bins=30)
    histogram_distribution = (hist_counts / max(hist_counts.sum(), 1)).astype(float).tolist()

    primary_breakdown = asset.get("primary_loss_breakdown", {"downtime_pct": 50, "incident_response_pct": 25})
    secondary_breakdown = asset.get("secondary_loss_breakdown", {"regulatory_penalties_pct": 20, "customer_remedy_reputation_pct": 5})
    primary_total_pct = sum(float(value) for value in primary_breakdown.values()) or 1.0
    secondary_total_pct = sum(float(value) for value in secondary_breakdown.values()) or 1.0
    primary_eal_lakhs = mean_loss * (primary_total_pct / 100.0)
    secondary_eal_lakhs = mean_loss * (secondary_total_pct / 100.0)
    reserve_lakhs = float(asset.get("suggested_incident_reserve_lakh", 0.0))

    return MonteCarloResponse(
        asset_id=int(asset["id"]),
        asset_name=str(asset["name"]),
        business_unit=str(asset["business_unit"]),
        criticality=str(asset["criticality"]),
        mean_loss_lakhs=mean_loss,
        p95_loss_lakhs=p95_loss,
        p99_loss_lakhs=p99_loss,
        trials=int(trials),
        distribution=histogram_distribution,
        control_efficiency=float(asset["control_efficiency"]),
        primary_eal_cr=round(primary_eal_lakhs / 100.0, 2),
        secondary_eal_cr=round(secondary_eal_lakhs / 100.0, 2),
        recommended_reserve_cr=round(reserve_lakhs / 100.0, 2),
        primary_loss_breakdown={key: float(value) for key, value in primary_breakdown.items()},
        secondary_loss_breakdown={key: float(value) for key, value in secondary_breakdown.items()},
        fair_cam={key: float(value) for key, value in fair_cam.items()},
        threat_community=list(asset.get("threat_community", [])),
        vendor_dependency=str(asset.get("vendor_dependency", "")),
        suggested_incident_reserve_lakh=reserve_lakhs,
        persona_explanations={key: str(value) for key, value in asset.get("persona_explanations", {}).items()},
    )


def simulate_candidate_controls(active_control_keys: list[str]) -> dict[str, object]:
    """Compute the org and BU-level impact for a selected mitigation set using the backend catalog."""
    normalized_keys: set[str] = set()
    for value in active_control_keys or []:
        raw_key = str(value).strip().lower()
        if raw_key in MITIGATION_CATALOG:
            normalized_keys.add(raw_key)
            continue
        try:
            normalized_id = int(value)
        except (TypeError, ValueError):
            normalized_id = None
        if normalized_id is not None:
            for key, control in MITIGATION_CATALOG.items():
                if int(control["id"]) == normalized_id:
                    normalized_keys.add(key)
                    break

    baseline_by_bu = {name: float(amount) for name, amount in BASELINE_BU_EAL_LAKHS.items()}
    current_eal_lakhs = float(sum(baseline_by_bu.values()))
    rollout_cost_lakh = 0.0
    total_reduction_lakh = 0.0
    projected_by_bu = dict(baseline_by_bu)

    for key in sorted(normalized_keys):
        control = MITIGATION_CATALOG[key]
        rollout_cost_lakh += float(control["cost_lakhs"])
        total_reduction_lakh += float(control["reduction_lakhs"])

        weights = control.get("allocation", {})
        total_weight = sum(float(weight) for weight in weights.values())
        if total_weight <= 0:
            total_weight = float(len(weights) or 1)

        for bu_name in baseline_by_bu:
            weight = float(weights.get(bu_name, 0.0))
            if weight <= 0:
                continue
            share = weight / total_weight
            projected_by_bu[bu_name] = max(baseline_by_bu[bu_name] - (float(control["reduction_lakhs"]) * share), 0.0)

    projected_eal_lakhs = float(sum(projected_by_bu.values()))
    reduction_pct = (abs(total_reduction_lakh) / current_eal_lakhs * 100.0) if current_eal_lakhs else 0.0
    if total_reduction_lakh >= 0:
        reduction_pct = (total_reduction_lakh / current_eal_lakhs * 100.0) if current_eal_lakhs else 0.0
    else:
        reduction_pct = (-total_reduction_lakh / current_eal_lakhs * 100.0) if current_eal_lakhs else 0.0

    reduction_delta_lakhs = max(current_eal_lakhs - projected_eal_lakhs, 0.0)
    if rollout_cost_lakh > 0 and reduction_delta_lakhs > 0:
        payback_months = rollout_cost_lakh / ((reduction_delta_lakhs / 12.0))
    else:
        payback_months = 0.0

    bu_comparison = [
        {
            "name": bu_name,
            "before": round(float(baseline_by_bu[bu_name]) / 100.0, 2),
            "after": round(float(projected_by_bu.get(bu_name, baseline_by_bu[bu_name])) / 100.0, 2),
        }
        for bu_name in ["Core Banking", "Payments", "Corporate IT", "Cards & Lending"]
    ]

    return {
        "current_eal_cr": round(current_eal_lakhs / 100.0, 2),
        "projected_eal_cr": round(projected_eal_lakhs / 100.0, 2),
        "reduction_lakh": round(total_reduction_lakh, 2),
        "reduction_pct": round(reduction_pct, 2),
        "rollout_cost_lakh": round(rollout_cost_lakh, 2),
        "payback_months": round(payback_months, 2),
        "bu_comparison": bu_comparison,
        "projected_bu_eal": projected_by_bu,
        "active_controls": sorted(normalized_keys),
        "current_eal_lakhs": current_eal_lakhs,
        "projected_eal_lakhs": projected_eal_lakhs,
        "baseline_eal_lakhs": current_eal_lakhs,
    }


def calculate_scenario(active_toggles: list[str]) -> ScenarioResponse:
    """Compute the scenario impact of enabled mitigations against the org baseline."""
    normalized_ids = []
    for value in active_toggles:
        try:
            normalized_ids.append(_normalize_action_id(value))
        except ValueError:
            continue

    enabled_actions = [action for action in MITIGATION_ACTIONS if int(action["id"]) in set(normalized_ids)]

    baseline_eal = float(BASELINE_EAL_LAKHS)
    reduction_lakhs = float(sum(float(action["reduction_lakhs"]) for action in enabled_actions))
    total_cost_lakhs = float(sum(float(action["cost_lakhs"]) for action in enabled_actions))
    projected_eal = max(50.0, baseline_eal - reduction_lakhs)
    reduction_pct = (reduction_lakhs / baseline_eal * 100.0) if baseline_eal else 0.0

    if total_cost_lakhs > 0 and reduction_lakhs > 0:
        payback_months = total_cost_lakhs / (reduction_lakhs / 12.0)
    else:
        payback_months = 0.0

    bu_totals: dict[str, float] = {}
    for asset in DIGITAL_ASSETS:
        bu = str(asset["business_unit"])
        bu_totals[bu] = bu_totals.get(bu, 0.0) + float(asset["baseline_eal_lakhs"])

    by_business_unit: dict[str, float] = {}
    for bu_name, bu_base in bu_totals.items():
        reduction_by_bu = 0.0
        for action in enabled_actions:
            reduction_by_bu += float(action["business_unit_impact"].get(bu_name, 0.0)) * (bu_base / 100.0)
        by_business_unit[bu_name] = max(bu_base - reduction_by_bu, 0.0)

    summary = (
        f"Baseline EAL {baseline_eal:.2f}L; projected EAL {projected_eal:.2f}L; net reduction {reduction_lakhs:.2f}L; "
        f"rollout cost {total_cost_lakhs:.2f}L; payback {payback_months:.1f} months."
    )

    return ScenarioResponse(
        projected_eal_lakhs=projected_eal,
        baseline_eal_lakhs=baseline_eal,
        reduction_lakhs=reduction_lakhs,
        reduction_pct=reduction_pct,
        total_cost_lakhs=total_cost_lakhs,
        payback_months=payback_months,
        enabled_action_ids=sorted({int(action["id"]) for action in enabled_actions}),
        by_business_unit=by_business_unit,
        summary=summary,
    )


def _evaluate_knapsack_for_budget(budget_lakhs: float) -> dict[str, object]:
    """Solve a 0/1 knapsack for the mitigation catalog using risk reduction as the objective."""
    budget_lakhs = max(0.0, float(budget_lakhs))
    candidates = []
    for key, control in MITIGATION_CATALOG.items():
        cost_lakhs = float(control.get("cost_lakhs", 0.0))
        reduction_lakhs = float(control.get("reduction_lakhs", 0.0))
        if reduction_lakhs <= 0:
            continue
        roi_multiplier = reduction_lakhs / cost_lakhs if cost_lakhs > 0 else 0.0
        candidates.append(
            {
                "id": int(control["id"]),
                "key": key,
                "name": str(control["name"]),
                "cost_lakhs": cost_lakhs,
                "reduction_lakhs": reduction_lakhs,
                "roi_multiplier": roi_multiplier,
            }
        )

    if not candidates:
        return {
            "selected": [],
            "selected_ids": [],
            "allocated_cost_lakhs": 0.0,
            "total_reduction_lakhs": 0.0,
            "remaining_budget_lakhs": budget_lakhs,
            "unfunded": [],
            "overall_rosi": 0.0,
        }

    budget_units = max(0, int(round(budget_lakhs * 100.0)))
    dp: list[tuple[int, list[int]]] = [(0, []) for _ in range(budget_units + 1)]

    for idx, candidate in enumerate(candidates):
        cost_units = max(0, int(round(float(candidate["cost_lakhs"]) * 100.0)))
        reduction_units = max(0, int(round(float(candidate["reduction_lakhs"]) * 100.0)))
        for capacity in range(budget_units, cost_units - 1, -1):
            previous_value, previous_selection = dp[capacity - cost_units]
            candidate_value = previous_value + reduction_units
            current_value, current_selection = dp[capacity]
            if candidate_value > current_value:
                dp[capacity] = (candidate_value, previous_selection + [idx])

    _, chosen_indices = max(dp, key=lambda item: item[0])
    selected_candidates = [candidates[idx] for idx in sorted(set(chosen_indices))]
    selected_ids = {int(item["id"]) for item in selected_candidates}

    selected_cost = sum(float(item["cost_lakhs"]) for item in selected_candidates)
    selected_reduction = sum(float(item["reduction_lakhs"]) for item in selected_candidates)
    remaining_budget = max(0.0, budget_lakhs - selected_cost)
    overall_rosi = selected_reduction / selected_cost if selected_cost > 0 else 0.0

    unfunded = []
    for candidate in candidates:
        if int(candidate["id"]) in selected_ids:
            continue
        if float(candidate["cost_lakhs"]) > budget_lakhs:
            reason = "Exceeds total budget"
        elif float(candidate["cost_lakhs"]) > remaining_budget:
            reason = "Exceeds remaining budget"
        else:
            reason = "Lower ROI than competing priorities"
        unfunded.append({
            "id": int(candidate["id"]),
            "name": candidate["name"],
            "cost_lakhs": float(candidate["cost_lakhs"]),
            "risk_saved_lakh": float(candidate["reduction_lakhs"]),
            "reason": reason,
        })

    return {
        "selected": selected_candidates,
        "selected_ids": sorted(selected_ids),
        "allocated_cost_lakhs": selected_cost,
        "total_reduction_lakhs": selected_reduction,
        "remaining_budget_lakhs": remaining_budget,
        "unfunded": unfunded,
        "overall_rosi": overall_rosi,
    }


def optimize_security_budget(budget_cr: float) -> dict[str, object]:
    """Compute the optimal control portfolio for a target budget in crore."""
    if budget_cr < 0:
        raise ValueError("budget_cr must be non-negative")

    budget_lakhs = max(0.0, float(budget_cr) * 100.0)
    knapsack = _evaluate_knapsack_for_budget(budget_lakhs)
    selected_controls = list(knapsack["selected"])
    total_cost_lakh = float(knapsack["allocated_cost_lakhs"])
    total_reduction_lakh = float(knapsack["total_reduction_lakhs"])
    remaining_budget_lakh = float(knapsack["remaining_budget_lakhs"])
    funded_controls = [
        {
            "id": int(control["id"]),
            "name": str(control["name"]),
            "cost_lakh": float(control["cost_lakhs"]),
            "cost_cr": round(float(control["cost_lakhs"]) / 100.0, 2),
            "risk_saved_lakh": float(control["reduction_lakhs"]),
            "risk_saved_cr": round(float(control["reduction_lakhs"]) / 100.0, 2),
            "roi_multiplier": round(float(control["roi_multiplier"]), 2),
        }
        for control in selected_controls
    ]
    unfunded_controls = [
        {
            "id": int(item["id"]),
            "name": str(item["name"]),
            "cost_lakh": float(item["cost_lakhs"]),
            "risk_saved_lakh": float(item["risk_saved_lakh"]),
            "reason": str(item["reason"]),
        }
        for item in knapsack["unfunded"]
    ]

    max_curve_budget = max(5.0, float(budget_cr))
    curve_points = []
    for index in range(15):
        point_budget_cr = round((max_curve_budget * index / 14.0), 2) if index > 0 else 0.0
        point_budget_lakhs = point_budget_cr * 100.0
        point_result = _evaluate_knapsack_for_budget(point_budget_lakhs)
        point_spend_cr = round(float(point_result["allocated_cost_lakhs"]) / 100.0, 2)
        point_risk_cr = round(float(point_result["total_reduction_lakhs"]) / 100.0, 2)
        curve_points.append({"spend_cr": point_spend_cr, "risk_reduction_cr": point_risk_cr})

    sweet_spot_cr = 0.0
    if curve_points:
        efficiency_candidates = [
            {"spend_cr": point["spend_cr"], "roi": point["risk_reduction_cr"] / point["spend_cr"] if point["spend_cr"] > 0 else 0.0}
            for point in curve_points if point["spend_cr"] > 0
        ]
        if efficiency_candidates:
            best = max(efficiency_candidates, key=lambda item: item["roi"])
            sweet_spot_cr = round(float(best["spend_cr"]), 2)

    executive_summary = (
        f"At a ₹{float(budget_cr):.2f} Cr budget, the model funds {len(funded_controls)} controls and captures ₹{total_reduction_lakh / 100.0:.2f} Cr in risk reduction for ₹{total_cost_lakh / 100.0:.2f} Cr in spend. "
        f"The steepest ROI sits around ₹{sweet_spot_cr:.2f} Cr; beyond that point, each additional rupee buys progressively less risk reduction."
    )

    result = {
        "budget_cr": round(float(budget_cr), 2),
        "allocated_spend_cr": round(total_cost_lakh / 100.0, 2),
        "unspent_lakh": round(max(0.0, budget_lakhs - total_cost_lakh), 2),
        "total_risk_reduced_cr": round(total_reduction_lakh / 100.0, 2),
        "overall_rosi": round(float(knapsack["overall_rosi"]), 2),
        "funded_controls": funded_controls,
        "unfunded_controls": unfunded_controls,
        "curve_points": curve_points,
        "sweet_spot_cr": sweet_spot_cr,
        "executive_summary": executive_summary,
        "recommended_action_ids": [int(control["id"]) for control in selected_controls],
        "total_cost_lakhs": round(total_cost_lakh, 2),
        "total_reduction_lakhs": round(total_reduction_lakh, 2),
        "remaining_budget_lakhs": round(remaining_budget_lakh, 2),
        "expected_eal_after_lakhs": max(50.0, float(BASELINE_EAL_LAKHS) - total_reduction_lakh),
        "rationale": [
            f"{control['name']} -> {float(control['reduction_lakhs']):.1f}L reduction at {float(control['cost_lakhs']):.1f}L cost"
            for control in selected_controls
        ],
    }
    return result


def optimize_budget(budget_lakh: float) -> OptimizerResponse:
    """Backward-compatible wrapper that accepts the legacy lakhs-based API contract."""
    if budget_lakh < 0:
        raise ValueError("budget_lakh must be non-negative")

    payload = optimize_security_budget(budget_lakh / 100.0)
    return OptimizerResponse(**payload)


__all__ = [
    "compute_monte_carlo",
    "calculate_scenario",
    "simulate_candidate_controls",
    "optimize_budget",
    "optimize_security_budget",
]
