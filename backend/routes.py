from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from backend.data import ACTIVE_ATTACK_STATE, ASSET_DATABASE, BASELINE_EAL_LAKHS, COMPLIANCE_MATRIX, DIGITAL_ASSETS, LIVE_TELEMETRY_EVENTS, MITIGATION_ACTIONS, REGULATORY_COMPLIANCE, REMEDIATION_TICKETS, append_live_telemetry_event, seed_live_telemetry_events
from backend.math_engine import calculate_scenario, compute_monte_carlo, optimize_budget, optimize_security_budget, simulate_candidate_controls
from backend.schemas import (
    BacklogTicketCreate,
    BacklogTicketStatusUpdate,
    BatchResolveRequest,
    ChatRequest,
    ChatResponse,
    MonteCarloResponse,
    OptimizerRequest,
    OptimizerResponse,
    ScenarioRequest,
    ScenarioResponse,
)

router = APIRouter()

ATTACK_TARGETS = {
    "ddos": "pay-gw-03",
    "ransomware": "core-pay-db-01",
    "credential_stuffing": "iam-sso-01",
}


def _deterministic_copilot_reply(query_text: str, persona: str) -> tuple[str, list[str], dict[str, float | int | str]]:
    normalized_query = (query_text or "").strip().lower()
    scenario = calculate_scenario([str(action["id"]) for action in MITIGATION_ACTIONS if action["default_on"]])
    optimizer = optimize_budget(120.0)
    top_asset = max(DIGITAL_ASSETS, key=lambda asset: float(asset["baseline_eal_lakhs"]))

    if not normalized_query:
        raise ValueError("Query cannot be empty.")

    if any(keyword in normalized_query for keyword in ["mfa", "authentication", "privileged"]):
        reply = (
            "MFA on privileged accounts remains one of the highest-yield controls. "
            f"It contributes {scenario.reduction_lakhs:.0f}L of the current default-enabled scenario reduction, "
            "and it is materially effective against identity-driven loss events."
        )
        cited_sources = ["scenario_model", "mitigation_actions"]
        verified_metrics = {
            "baseline_org_eal_lakhs": float(BASELINE_EAL_LAKHS),
            "projected_eal_lakhs": float(scenario.projected_eal_lakhs),
            "reduction_lakhs": float(scenario.reduction_lakhs),
        }
    elif any(keyword in normalized_query for keyword in ["eal", "exposure", "annual loss", "risk"]):
        reply = (
            f"The current baseline org EAL is ₹{BASELINE_EAL_LAKHS:.0f}L. "
            f"With the default-enabled mitigation set, projected EAL is ₹{scenario.projected_eal_lakhs:.0f}L, "
            f"which is a reduction of ₹{scenario.reduction_lakhs:.0f}L ({scenario.reduction_pct:.0f}%)."
        )
        cited_sources = ["baseline_eal", "scenario_model"]
        verified_metrics = {
            "baseline_org_eal_lakhs": float(BASELINE_EAL_LAKHS),
            "projected_eal_lakhs": float(scenario.projected_eal_lakhs),
            "reduction_pct": float(scenario.reduction_pct),
        }
    elif any(keyword in normalized_query for keyword in ["compliance", "framework", "rbi", "nist", "iso", "sebi"]):
        compliant_scores = ", ".join(f"{name}: {meta['score']}%" for name, meta in REGULATORY_COMPLIANCE.items())
        reply = (
            f"The measured compliance posture is: {compliant_scores}. "
            f"RBI remains the lowest at {REGULATORY_COMPLIANCE['RBI']['score']}%, which is consistent with the network segmentation and access logging gaps."
        )
        cited_sources = ["compliance_matrix"]
        verified_metrics = {
            "rbi_score": REGULATORY_COMPLIANCE["RBI"]["score"],
            "nist_score": REGULATORY_COMPLIANCE["NIST CSF"]["score"],
            "iso_score": REGULATORY_COMPLIANCE["ISO 27001"]["score"],
        }
    elif any(keyword in normalized_query for keyword in ["highest risk", "business unit", "risk by business", "top risk"]):
        reply = (
            f"The highest-risk asset in the current dataset is {top_asset['name']} in {top_asset['business_unit']} with an EAL of ₹{top_asset['baseline_eal_lakhs']:.0f}L. "
            f"This is the largest single contributor to the enterprise exposure profile."
        )
        cited_sources = ["digital_assets", "baseline_eal"]
        verified_metrics = {
            "top_asset_name": top_asset["name"],
            "top_asset_eal_lakhs": float(top_asset["baseline_eal_lakhs"]),
        }
    elif any(keyword in normalized_query for keyword in ["rosi", "return", "invest", "budget"]):
        reply = (
            f"At a ₹120L budget, the optimizer recommends {optimizer.recommended_action_ids}. "
            f"This yields ₹{optimizer.total_reduction_lakhs:.0f}L in reduction at a cost of ₹{optimizer.total_cost_lakhs:.0f}L, "
            f"with a projected post-investment EAL of ₹{optimizer.expected_eal_after_lakhs:.0f}L."
        )
        cited_sources = ["optimizer_model"]
        verified_metrics = {
            "optimizer_budget_lakhs": 120.0,
            "optimizer_total_reduction_lakhs": float(optimizer.total_reduction_lakhs),
            "optimizer_total_cost_lakhs": float(optimizer.total_cost_lakhs),
            "optimizer_expected_eal_after_lakhs": float(optimizer.expected_eal_after_lakhs),
        }
    else:
        reply = (
            f"Using the verified local model, the current baseline org EAL is ₹{BASELINE_EAL_LAKHS:.0f}L and the default-enabled scenario projects ₹{scenario.projected_eal_lakhs:.0f}L. "
            f"The most material control driver is {top_asset['name']} in {top_asset['business_unit']}, which is why it is prioritized in the current exposure model."
        )
        cited_sources = ["scenario_model", "digital_assets"]
        verified_metrics = {
            "baseline_org_eal_lakhs": float(BASELINE_EAL_LAKHS),
            "projected_eal_lakhs": float(scenario.projected_eal_lakhs),
            "top_asset_name": top_asset["name"],
        }

    if persona and persona.lower() == "analyst":
        reply = f"[{persona}] {reply}"

    return reply, cited_sources, verified_metrics


@router.get("/telemetry/live-feed")
def get_live_telemetry_feed() -> list[dict[str, Any]]:
    seed_live_telemetry_events()
    return [dict(event) for event in LIVE_TELEMETRY_EVENTS[:10]]


@router.post("/telemetry/trigger-drill")
def trigger_attack_drill(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    attack_request = payload or {}
    attack_type = str(attack_request.get("attack_type") or "ddos").strip().lower()
    normalized_attack = attack_type if attack_type in ATTACK_TARGETS else "ddos"
    target_asset = ATTACK_TARGETS[normalized_attack]
    asset = next((item for item in ASSET_DATABASE if str(item["name"]).lower() == target_asset.lower()), None)
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Target asset '{target_asset}' not found.")

    spike_cr = 1.35
    ACTIVE_ATTACK_STATE.update({
        "is_attack_active": True,
        "attack_type": normalized_attack,
        "target_asset": target_asset,
        "eal_spike_cr": spike_cr,
        "last_reset_at": None,
    })

    append_live_telemetry_event(
        source="Cloudflare WAF",
        target_asset=target_asset,
        event_type="VOL_ATTACK",
        severity="CRITICAL",
        message=f"Volumetric {normalized_attack.replace('_', ' ')} campaign detected against {target_asset}.",
        status="ANOMALY_DETECTED",
    )
    append_live_telemetry_event(
        source="CrowdStrike",
        target_asset=target_asset,
        event_type="HOSTILE_ACTIVITY",
        severity="CRITICAL",
        message=f"Security controls show sustained hostile activity and evidence of rapid lateral spread.",
        status="ANOMALY_DETECTED",
    )
    append_live_telemetry_event(
        source="Defender",
        target_asset=target_asset,
        event_type="IR_ALERT",
        severity="CRITICAL",
        message=f"SOC escalation: {normalized_attack.replace('_', ' ').title()} drill active; EAL temporarily elevated by ₹{spike_cr:.2f} Cr.",
        status="BLOCKED",
    )

    ticket = {
        "id": _next_backlog_id(),
        "finding": f"Emergency {normalized_attack.replace('_', ' ').title()} mitigation required on {target_asset}",
        "asset_id": target_asset,
        "business_unit": str(asset["business_unit"]),
        "eal_impact_lakh": float(asset.get("baseline_eal_lakhs", 0.0)) * 0.15,
        "owner": "SOC Escalation",
        "priority": "CRITICAL",
        "status": "OPEN",
        "sla_hours_remaining": 12,
        "remediation_command": f"sudo /opt/cyberisk/bin/neutralize --asset {target_asset} --attack {normalized_attack} --priority critical",
        "jira_key": None,
    }
    REMEDIATION_TICKETS.insert(0, ticket)

    metrics = compute_monte_carlo(asset_id=target_asset, trials=50000)
    return {
        "attack_active": True,
        "attack_type": normalized_attack,
        "target_asset": target_asset,
        "baseline_eal_cr": round(float(asset["baseline_eal_lakhs"]) / 100.0, 2),
        "eal_cr": round(float(metrics.mean_loss_lakhs) / 100.0, 2),
        "eal_spike_cr": spike_cr,
        "live_events": LIVE_TELEMETRY_EVENTS[:10],
        "ticket_id": ticket["id"],
    }


@router.post("/telemetry/reset-drill")
def reset_attack_drill(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    ACTIVE_ATTACK_STATE.update({
        "is_attack_active": False,
        "attack_type": None,
        "target_asset": None,
        "eal_spike_cr": 0.0,
        "last_reset_at": None,
    })
    append_live_telemetry_event(
        source="SOC Automation",
        target_asset="global",
        event_type="RESET",
        severity="INFO",
        message="Attack drill neutralized and baseline loss thresholds restored.",
        status="SCANNED",
    )
    return {
        "attack_active": False,
        "attack_type": None,
        "target_asset": None,
        "message": "Baseline threat posture restored.",
        "live_events": LIVE_TELEMETRY_EVENTS[:10],
    }


@router.get("/overview/metrics")
def get_overview_metrics() -> dict[str, Any]:
    total_eal = float(BASELINE_EAL_LAKHS) / 100.0
    total_assets = len(ASSET_DATABASE)
    critical_assets = sum(1 for asset in ASSET_DATABASE if asset["criticality"] in {"Critical", "High"})
    scenario = calculate_scenario([str(action["id"]) for action in MITIGATION_ACTIONS if action["default_on"]])

    return {
        "current_eal_cr": round(total_eal, 2),
        "worst_case_var_cr": 9.15,
        "enterprise_score": 73,
        "open_findings": 17,
        "asset_count": total_assets,
        "critical_asset_count": critical_assets,
        "monthly_trend": [
            {"month": "Sep", "eal_cr": 6.4},
            {"month": "Oct", "eal_cr": 6.2},
            {"month": "Nov", "eal_cr": 5.9},
            {"month": "Dec", "eal_cr": 5.7},
            {"month": "Jan", "eal_cr": 5.5},
            {"month": "Feb", "eal_cr": 5.3},
            {"month": "Mar", "eal_cr": 5.1},
            {"month": "Apr", "eal_cr": 4.9},
            {"month": "May", "eal_cr": 4.7},
            {"month": "Jun", "eal_cr": 4.9},
            {"month": "Jul", "eal_cr": 4.8},
            {"month": "Aug", "eal_cr": 4.82},
        ],
        "framework_readiness": {
            "ISO 27001": 82,
            "NIST CSF": 76,
            "CIS Controls": 88,
            "RBI": 69,
            "SEBI": 74,
        },
        "scenario": {
            "baseline_eal_lakhs": scenario.baseline_eal_lakhs,
            "projected_eal_lakhs": scenario.projected_eal_lakhs,
            "reduction_lakhs": scenario.reduction_lakhs,
            "reduction_pct": scenario.reduction_pct,
        },
    }


@router.get("/quant/assets")
def get_quant_assets() -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for asset in ASSET_DATABASE:
        payload.append(
            {
                "id": asset["id"],
                "name": asset["name"],
                "business_unit": asset["business_unit"],
                "criticality": asset["criticality"],
                "eal_lakhs": asset["baseline_eal_lakhs"],
                "var_95_lakhs": asset["var_95_lakhs"],
                "var_95_cr": asset.get("var_95_cr", round(float(asset["var_95_lakhs"]) / 100.0, 2)),
                "control_efficiency": asset["control_efficiency"],
                "telemetry_source": asset.get("telemetry_source"),
                "technical_details": asset.get("technical_details", {}),
                "loss_breakdown": asset.get("loss_breakdown", {}),
                "primary_loss_breakdown": asset.get("primary_loss_breakdown", {}),
                "secondary_loss_breakdown": asset.get("secondary_loss_breakdown", {}),
                "fair_cam": asset.get("fair_cam", {}),
                "threat_community": asset.get("threat_community", []),
                "vendor_dependency": asset.get("vendor_dependency", ""),
                "suggested_incident_reserve_lakh": asset.get("suggested_incident_reserve_lakh", 0.0),
                "persona_explanations": asset.get("persona_explanations", {}),
                "explanation": asset.get("explanation", ""),
                "loss_params": asset["loss_params"],
            }
        )
    return payload


@router.get("/quant/assets/{asset_id}/explain")
def get_asset_explanation(asset_id: str, persona: str = Query(default="executive")) -> dict[str, Any]:
    normalized = str(asset_id).strip()
    asset = next((item for item in ASSET_DATABASE if str(item["name"]).lower() == normalized.lower() or int(item["id"]) == int(normalized)), None)
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found.")

    ranked_assets = sorted(ASSET_DATABASE, key=lambda item: float(item["baseline_eal_lakhs"]), reverse=True)
    rank = ranked_assets.index(asset) + 1
    eal_cr = float(asset["baseline_eal_lakhs"]) / 100.0
    var_95_cr = float(asset.get("var_95_cr", float(asset["var_95_lakhs"]) / 100.0))
    persona_key = (persona or "executive").strip().lower()
    if persona_key not in {"executive", "ciso", "analyst"}:
        persona_key = "executive"

    explanation = asset.get("persona_explanations", {}).get(persona_key, asset.get("explanation", ""))

    return {
        "asset_id": asset["id"],
        "asset_name": asset["name"],
        "business_unit": asset["business_unit"],
        "criticality": asset["criticality"],
        "persona": persona_key,
        "persona_explanations": asset.get("persona_explanations", {}),
        "eal_contribution_cr": round(eal_cr, 2),
        "var_95_cr": round(var_95_cr, 2),
        "telemetry_source": asset.get("telemetry_source"),
        "technical_details": asset.get("technical_details", {}),
        "loss_breakdown": asset.get("loss_breakdown", {}),
        "primary_loss_breakdown": asset.get("primary_loss_breakdown", {"downtime_pct": 50, "incident_response_pct": 25}),
        "secondary_loss_breakdown": asset.get("secondary_loss_breakdown", {"regulatory_penalties_pct": 20, "customer_remedy_reputation_pct": 5}),
        "fair_cam": asset.get("fair_cam", {"threat_resistance_pct": 0, "loss_mitigation_pct": 0}),
        "threat_community": asset.get("threat_community", []),
        "vendor_dependency": asset.get("vendor_dependency", ""),
        "suggested_incident_reserve_lakh": float(asset.get("suggested_incident_reserve_lakh", 0.0)),
        "suggested_incident_reserve_cr": round(float(asset.get("suggested_incident_reserve_lakh", 0.0)) / 100.0, 2),
        "control_efficiency": asset["control_efficiency"],
        "explanation": explanation,
        "rank": rank,
    }


@router.post("/quant/monte-carlo/{asset_id}", response_model=MonteCarloResponse)
def monte_carlo_for_asset(
    asset_id: str,
    payload: dict[str, int] | None = Body(default=None),
    trials: int | None = Query(default=None, ge=1),
) -> MonteCarloResponse:
    requested_trials = trials
    if payload and isinstance(payload, dict):
        requested_trials = payload.get("trials", requested_trials)
    if requested_trials is None:
        requested_trials = 50000
    try:
        return compute_monte_carlo(asset_id=asset_id, trials=int(requested_trials))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/scenario/simulate", response_model=ScenarioResponse)
def simulate_scenario(payload: ScenarioRequest) -> ScenarioResponse:
    active_keys = list(payload.active_controls)
    if not active_keys and payload.selected_action_ids:
        active_keys = [
            next((action["key"] for action in MITIGATION_ACTIONS if int(action["id"]) == int(action_id)), str(action_id))
            for action_id in payload.selected_action_ids
        ]
    if not active_keys:
        active_keys = [
            action["key"] for action in MITIGATION_ACTIONS if action.get("default_on")
        ]

    response_dict = simulate_candidate_controls(active_keys)
    projected_by_bu = response_dict.get("projected_bu_eal", {})
    response = ScenarioResponse(
        projected_eal_lakhs=float(response_dict.get("projected_eal_lakhs", 0.0)),
        baseline_eal_lakhs=float(response_dict.get("baseline_eal_lakhs", 0.0)),
        reduction_lakhs=float(response_dict.get("reduction_lakh", 0.0)),
        reduction_pct=float(response_dict.get("reduction_pct", 0.0)),
        total_cost_lakhs=float(response_dict.get("rollout_cost_lakh", 0.0)),
        payback_months=float(response_dict.get("payback_months", 0.0)),
        enabled_action_ids=[
            int(action["id"]) for action in MITIGATION_ACTIONS if action.get("key") in response_dict.get("active_controls", [])
        ],
        by_business_unit={key: float(value) for key, value in projected_by_bu.items()},
        summary=(
            f"Baseline EAL {float(response_dict.get('baseline_eal_lakhs', 0.0)):.2f}L; "
            f"projected EAL {float(response_dict.get('projected_eal_lakhs', 0.0)):.2f}L; "
            f"reduction {float(response_dict.get('reduction_lakh', 0.0)):.2f}L; "
            f"payback {float(response_dict.get('payback_months', 0.0)):.2f} months."
        ),
        current_eal_cr=float(response_dict.get("current_eal_cr", 0.0)),
        projected_eal_cr=float(response_dict.get("projected_eal_cr", 0.0)),
        reduction_lakh=float(response_dict.get("reduction_lakh", 0.0)),
        rollout_cost_lakh=float(response_dict.get("rollout_cost_lakh", 0.0)),
        bu_comparison=response_dict.get("bu_comparison", []),
        active_controls=list(response_dict.get("active_controls", [])),
    )

    if payload.business_unit:
        response.by_business_unit = {
            k: v for k, v in response.by_business_unit.items() if k == payload.business_unit
        }
    if payload.budget_lakhs is not None:
        response.total_cost_lakhs = min(response.total_cost_lakhs, float(payload.budget_lakhs))
    return response


@router.post("/optimizer/optimize", response_model=OptimizerResponse)
def optimize_budget_route(payload: OptimizerRequest) -> OptimizerResponse:
    requested_budget = payload.budget_cr
    if requested_budget is None and payload.budget_lakhs is not None:
        requested_budget = payload.budget_lakhs / 100.0
    if requested_budget is None:
        raise HTTPException(status_code=400, detail="budget_cr or budget_lakhs is required")

    result = optimize_security_budget(float(requested_budget))
    return OptimizerResponse(**result)


@router.get("/compliance/frameworks")
def get_framework_readiness() -> dict[str, int]:
    readiness = {
        "ISO 27001": 82,
        "NIST CSF": 76,
        "CIS Controls": 88,
        "RBI CSF": 69,
        "SEBI CSCRF": 71,
        "Overall": 77,
    }
    return readiness


@router.get("/compliance/matrix")
def get_compliance_matrix() -> dict[str, Any]:
    return {
        "frameworks": {
            "ISO 27001": 82,
            "NIST CSF": 76,
            "CIS Controls": 88,
            "RBI CSF": 69,
            "SEBI CSCRF": 71,
            "Overall": 77,
        },
        "controls": COMPLIANCE_MATRIX,
        "summary": {
            "total_controls": len(COMPLIANCE_MATRIX),
            "evidenced": sum(1 for item in COMPLIANCE_MATRIX if item["status"] == "EVIDENCED"),
            "partial": sum(1 for item in COMPLIANCE_MATRIX if item["status"] == "PARTIAL"),
            "gap": sum(1 for item in COMPLIANCE_MATRIX if item["status"] == "GAP"),
        },
    }


@router.get("/compliance/export-report")
def export_compliance_report() -> dict[str, Any]:
    report_lines = [
        "CyberRiskIQ Compliance Readiness Summary",
        "======================================",
        "",
        "Framework readiness:",
    ]
    for key, value in {
        "ISO 27001": 82,
        "NIST CSF": 76,
        "CIS Controls": 88,
        "RBI CSF": 69,
        "SEBI CSCRF": 71,
        "Overall": 77,
    }.items():
        report_lines.append(f"- {key}: {value}%")

    report_lines.extend(["", "Control matrix summary:"])
    for control in COMPLIANCE_MATRIX:
        report_lines.append(
            f"- {control['id']} | {control['name']} | Status: {control['status']} | Coverage: {control['coverage_pct']}% | Penalty risk: ₹{control['penalty_risk_cr']:.2f} Cr"
        )

    report_lines.extend(["", "Priority remediation notes:"])
    for control in COMPLIANCE_MATRIX:
        if control["status"] != "EVIDENCED":
            report_lines.append(f"- {control['name']}: {control['recommended_action']}")

    return {
        "file_name": "compliance-readiness-report.txt",
        "content_type": "text/plain",
        "report": "\n".join(report_lines),
        "summary": {
            "overall_score": 77,
            "controls_reviewed": len(COMPLIANCE_MATRIX),
            "controls_needing_attention": sum(1 for item in COMPLIANCE_MATRIX if item["status"] != "EVIDENCED"),
        },
    }


def _normalize_status(value: str | None) -> str:
    normalized = (value or "").strip().upper()
    if normalized == "IN PROGRESS":
        return "IN_PROGRESS"
    if normalized == "BLOCKED":
        return "IN_PROGRESS"
    if normalized == "RESOLVED":
        return "DONE"
    if normalized in {"OPEN", "IN_PROGRESS", "DONE"}:
        return normalized
    raise ValueError(f"Unsupported ticket status: {value}")


def _next_backlog_id() -> str:
    existing_ids = [ticket["id"] for ticket in REMEDIATION_TICKETS if str(ticket.get("id", "")).startswith("SEC-")]
    if not existing_ids:
        return "SEC-801"
    highest = 0
    for ticket_id in existing_ids:
        try:
            value = int(str(ticket_id).split("-")[-1])
            highest = max(highest, value)
        except ValueError:
            continue
    return f"SEC-{highest + 1}"


def _estimate_eal_for_asset(asset_id: str) -> float:
    mapping = {
        "core-pay-db-01": 68.0,
        "pay-gw-03": 61.0,
        "corp-fs-02": 48.0,
        "cards-api-legacy": 22.0,
        "iam-sso-01": 19.0,
        "branch-pos-fleet": 16.0,
        "org-wide": 72.0,
    }
    return mapping.get(str(asset_id).strip(), 24.0)


@router.get("/backlog/tickets")
def get_remediation_tickets(status: str | None = None) -> list[dict[str, Any]]:
    filtered = list(REMEDIATION_TICKETS)
    if status:
        normalized = _normalize_status(status)
        filtered = [ticket for ticket in filtered if str(ticket.get("status", "OPEN")).upper() == normalized]
    return filtered


@router.post("/backlog/tickets")
def create_remediation_ticket(payload: BacklogTicketCreate) -> dict[str, Any]:
    if not payload.finding or not payload.finding.strip():
        raise HTTPException(status_code=400, detail="Finding title is required.")

    normalized_status = _normalize_status(payload.status)
    priority = str(payload.priority).upper()
    asset_id = str(payload.asset_id).strip()
    eal_impact = float(payload.eal_impact_lakh if payload.eal_impact_lakh is not None else _estimate_eal_for_asset(asset_id))
    remediation_command = payload.remediation_command or (
        f"sudo /opt/cyberisk/bin/patch-asset --asset {asset_id} --owner '{payload.owner}' --priority {priority.lower()}"
    )
    ticket = {
        "id": _next_backlog_id(),
        "finding": payload.finding.strip(),
        "asset_id": asset_id,
        "business_unit": payload.business_unit.strip(),
        "eal_impact_lakh": eal_impact,
        "owner": payload.owner.strip(),
        "priority": priority,
        "status": normalized_status,
        "sla_hours_remaining": int(payload.sla_hours_remaining if payload.sla_hours_remaining is not None else {"CRITICAL": 24, "HIGH": 36, "MEDIUM": 48, "LOW": 72}.get(priority, 72)),
        "remediation_command": remediation_command,
        "jira_key": None,
    }
    REMEDIATION_TICKETS.insert(0, ticket)
    return ticket


@router.patch("/backlog/tickets/{ticket_id}/status")
def update_remediation_ticket_status(ticket_id: str, payload: BacklogTicketStatusUpdate) -> dict[str, Any]:
    ticket = next((item for item in REMEDIATION_TICKETS if str(item["id"]) == str(ticket_id)), None)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found.")

    new_status = _normalize_status(payload.status)
    ticket["status"] = new_status
    if new_status == "DONE":
        ticket["sla_hours_remaining"] = 0
    updated_org_eal = sum(float(item.get("eal_impact_lakh", 0.0)) for item in REMEDIATION_TICKETS if str(item.get("status", "OPEN")).upper() == "DONE")
    return {
        "ticket": ticket,
        "status": new_status,
        "eal_reduction_lakh": float(ticket.get("eal_impact_lakh", 0.0)) if new_status == "DONE" else 0.0,
        "updated_org_eal_lakhs": round(updated_org_eal, 2),
        "message": "Ticket resolved — ₹%s Lakhs eliminated from EAL" % round(float(ticket.get("eal_impact_lakh", 0.0)), 2) if new_status == "DONE" else "Ticket status updated.",
    }


@router.post("/backlog/tickets/{ticket_id}/jira-sync")
def sync_ticket_to_jira(ticket_id: str) -> dict[str, Any]:
    ticket = next((item for item in REMEDIATION_TICKETS if str(item["id"]) == str(ticket_id)), None)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found.")

    suffix = 4900 + sum(1 for item in REMEDIATION_TICKETS if item.get("jira_key"))
    ticket["jira_key"] = f"JIRA-{suffix}"
    return {"ticket_id": ticket["id"], "jira_key": ticket["jira_key"], "message": "Jira sync generated."}


@router.post("/backlog/batch-resolve")
def batch_resolve_tickets(payload: BatchResolveRequest) -> dict[str, Any]:
    selected_ids = [str(ticket_id).strip() for ticket_id in payload.ticket_ids if str(ticket_id).strip()]
    total_reduction = 0.0
    resolved = []
    for ticket_id in selected_ids:
        ticket = next((item for item in REMEDIATION_TICKETS if str(item["id"]) == ticket_id), None)
        if ticket is None:
            continue
        if str(ticket.get("status", "OPEN")).upper() != "DONE":
            ticket["status"] = "DONE"
            ticket["sla_hours_remaining"] = 0
            total_reduction += float(ticket.get("eal_impact_lakh", 0.0))
            resolved.append(ticket["id"])
    return {
        "resolved_count": len(resolved),
        "resolved_ticket_ids": resolved,
        "total_eal_reduced_lakh": round(total_reduction, 2),
        "message": f"Resolved {len(resolved)} tickets and reclaimed ₹{round(total_reduction, 2)} Lakhs.",
    }


@router.post("/chat/message", response_model=ChatResponse)
def chat_message(payload: ChatRequest) -> ChatResponse:
    query_text = payload.effective_query
    if not query_text:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        persona = str(payload.persona or (payload.context or {}).get("persona", "Executive"))
        reply, cited_sources, verified_metrics = _deterministic_copilot_reply(query_text, persona)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ChatResponse(
        reply=reply,
        cited_sources=cited_sources,
        confidence=0.9,
        status="ok",
        verified_metrics=verified_metrics,
    )
