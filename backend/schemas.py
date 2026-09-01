from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ScenarioRequest(BaseModel):
    active_controls: list[str] = Field(default_factory=list)
    selected_action_ids: list[int] = Field(default_factory=list)
    business_unit: str | None = None
    budget_lakhs: float | None = None
    include_regulatory: bool = False
    scenario_name: str | None = None


class ScenarioResponse(BaseModel):
    projected_eal_lakhs: float = 0.0
    baseline_eal_lakhs: float = 0.0
    reduction_lakhs: float = 0.0
    reduction_pct: float = 0.0
    total_cost_lakhs: float = 0.0
    payback_months: float = 0.0
    enabled_action_ids: list[int] = Field(default_factory=list)
    by_business_unit: dict[str, float] = Field(default_factory=dict)
    summary: str = ""
    current_eal_cr: float = 0.0
    projected_eal_cr: float = 0.0
    reduction_lakh: float = 0.0
    rollout_cost_lakh: float = 0.0
    bu_comparison: list[dict[str, float | str]] = Field(default_factory=list)
    active_controls: list[str] = Field(default_factory=list)


class OptimizerRequest(BaseModel):
    budget_cr: float | None = Field(default=None, ge=0)
    budget_lakhs: float | None = Field(default=None, ge=0)
    candidate_action_ids: list[int] | None = None
    max_actions: int | None = Field(default=None, ge=1)

    @property
    def effective_budget_lakhs(self) -> float:
        if self.budget_lakhs is not None:
            return float(self.budget_lakhs)
        if self.budget_cr is not None:
            return float(self.budget_cr) * 100.0
        raise ValueError("budget_cr or budget_lakhs is required")


class OptimizerResponse(BaseModel):
    budget_cr: float = 0.0
    allocated_spend_cr: float = 0.0
    unspent_lakh: float = 0.0
    total_risk_reduced_cr: float = 0.0
    overall_rosi: float = 0.0
    funded_controls: list[dict[str, Any]] = Field(default_factory=list)
    unfunded_controls: list[dict[str, Any]] = Field(default_factory=list)
    curve_points: list[dict[str, float]] = Field(default_factory=list)
    sweet_spot_cr: float = 0.0
    executive_summary: str = ""
    recommended_action_ids: list[int] = Field(default_factory=list)
    total_cost_lakhs: float = 0.0
    total_reduction_lakhs: float = 0.0
    remaining_budget_lakhs: float = 0.0
    expected_eal_after_lakhs: float = 0.0
    rationale: list[str] = Field(default_factory=list)


class MonteCarloResponse(BaseModel):
    asset_id: int
    asset_name: str
    business_unit: str
    criticality: str
    mean_loss_lakhs: float
    p95_loss_lakhs: float
    p99_loss_lakhs: float
    trials: int
    distribution: list[float] = Field(default_factory=list)
    control_efficiency: float
    primary_eal_cr: float = 0.0
    secondary_eal_cr: float = 0.0
    recommended_reserve_cr: float = 0.0
    primary_loss_breakdown: dict[str, float] = Field(default_factory=dict)
    secondary_loss_breakdown: dict[str, float] = Field(default_factory=dict)
    fair_cam: dict[str, float] = Field(default_factory=dict)
    threat_community: list[str] = Field(default_factory=list)
    vendor_dependency: str = ""
    suggested_incident_reserve_lakh: float = 0.0
    persona_explanations: dict[str, str] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    message: str | None = None
    query: str | None = None
    persona: str = "Executive"
    context: dict[str, Any] | None = None

    @property
    def effective_query(self) -> str:
        return (self.query or self.message or "").strip()


class ChatResponse(BaseModel):
    reply: str
    cited_sources: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    status: Literal["ok", "partial", "error"] = "ok"
    verified_metrics: dict[str, Any] = Field(default_factory=dict)


class BacklogTicket(BaseModel):
    id: str
    finding: str
    asset_id: str
    business_unit: str
    eal_impact_lakh: float = Field(default=0.0, ge=0.0)
    owner: str
    priority: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    status: Literal["OPEN", "IN_PROGRESS", "DONE"]
    sla_hours_remaining: int = Field(default=72, ge=0)
    remediation_command: str = ""
    jira_key: str | None = None


class BacklogTicketCreate(BaseModel):
    finding: str = Field(..., min_length=1)
    asset_id: str = Field(..., min_length=1)
    business_unit: str = Field(..., min_length=1)
    eal_impact_lakh: float | None = Field(default=None, ge=0)
    owner: str = Field(..., min_length=1)
    priority: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = "HIGH"
    status: Literal["OPEN", "IN_PROGRESS", "DONE"] = "OPEN"
    sla_hours_remaining: int | None = Field(default=None, ge=0)
    remediation_command: str | None = None


class BacklogTicketStatusUpdate(BaseModel):
    status: Literal["OPEN", "IN_PROGRESS", "DONE"] = Field(...)


class BatchResolveRequest(BaseModel):
    ticket_ids: list[str] = Field(default_factory=list)


class TicketUpdateRequest(BaseModel):
    ticket_id: str = Field(..., min_length=1)
    status: Literal["open", "in_progress", "blocked", "resolved", "closed", "OPEN", "IN_PROGRESS", "DONE"] | None = None
    owner: str | None = None
    priority: Literal["low", "medium", "high", "critical", "LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = None
    resolution_note: str | None = None
    remediation_pct: float | None = Field(default=None, ge=0, le=100)
