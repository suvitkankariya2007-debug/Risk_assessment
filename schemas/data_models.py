"""
Shared Pydantic v2 Typed Contracts
Deterministic Cyber Risk Quantification (CRQ) Platform

Developer A: Frozen, strict core mathematical contracts (Section 1)
Developer B: Mutable API/UI contracts preserved for backward compatibility (Section 2)
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


# ============================================================================
# SECTION 1: DEVELOPER A — CORE MATHEMATICAL ENGINE CONTRACTS
# All models use frozen=True, strict=True per specification
# ============================================================================

class ThreatContext(BaseModel):
    """Unified input contract for the deterministic compute pipeline."""
    model_config = ConfigDict(frozen=True, strict=True)

    cve_id: str
    description: str
    asset_name: str
    asset_replacement_cost_cr: float
    daily_revenue_impact_cr: float
    regulatory_tier: str  # "TIER_1_CRITICAL" or "TIER_2_STANDARD"
    cvss_base_score: float
    cvss_vector: str
    features: Dict[str, bool]  # 16 EPSS boolean flags
    ref_count: int
    proposed_control_cost_lakhs: float


class EPSSPrediction(BaseModel):
    """Output of the EPSS Exploit Prediction Engine."""
    model_config = ConfigDict(frozen=True, strict=True)

    cve_id: str
    epss_probability: float = Field(ge=0.0, le=1.0)
    percentile: float = Field(ge=0.0, le=100.0)
    # Real computed logistic z-score (replaces the hardcoded -1.5 placeholder).
    # 0.0 default keeps older constructions backward compatible.
    z_score: float = 0.0
    # True when probability/percentile came from the live FIRST.org EPSS API.
    live_epss: bool = False



class FAIRSimulationResult(BaseModel):
    """Output of the Open FAIR v3.0 Monte Carlo engine."""
    model_config = ConfigDict(frozen=True, strict=True)

    expected_annual_loss_cr: float
    value_at_risk_95_cr: float
    primary_loss_cr: float
    secondary_loss_cr: float
    iterations: int


class XAITrustResult(BaseModel):
    """Output of the XAI Trust Auditor (Mirtaheri et al., 2025)."""
    model_config = ConfigDict(frozen=True, strict=True)

    trust_score_pct: float = Field(ge=0.0, le=100.0)
    salient_tokens: List[str]
    alignment_status: str


class ROSIOptimizationResult(BaseModel):
    """Output of the MILP 0/1 Knapsack ROSI Optimizer with Gordon-Loeb ceiling."""
    model_config = ConfigDict(frozen=True, strict=True)

    control_cost_cr: float
    risk_reduced_cr: float
    net_benefit_cr: float
    rosi_percentage: float
    gordon_loeb_cap_cr: float
    is_economically_viable: bool


# ── Phase-1 extension engines (frozen, same contract style) ─────────────────

class BusinessProfileResult(BaseModel):
    """Output of the business-profile builder (unit + segment hierarchy)."""
    model_config = ConfigDict(frozen=True, strict=True)

    business_unit_name: str
    sector: str
    country: str
    employee_count: Optional[int] = None
    segments: List[str]
    total_revenue_cr: float


class SegmentRiskResult(BaseModel):
    """Output of the segment impact/risk engine."""
    model_config = ConfigDict(frozen=True, strict=True)

    impact_operational: float
    impact_financial: float
    impact_w: float
    seg_revenue_cr: float
    seg_impact_cr: float
    risk_w: float
    seg_risk_cr: float
    risk_weighting_factor: float = 1.0


class ControlMaturityResult(BaseModel):
    """Output of the control-maturity efficacy engine."""
    model_config = ConfigDict(frozen=True, strict=True)

    maturity_level: str
    maturity_multiplier: float
    efficacy_t: float
    control_efficacy_t: float


class ZRosiResult(BaseModel):
    """Output of the cost-adjusted ROSI (v2) engine."""
    model_config = ConfigDict(frozen=True, strict=True)

    ale_cr: float
    control_efficacy_t: float
    control_cost_cr: float
    cost_rate: float
    z_rosi: float


class CiaExposureResult(BaseModel):
    """Output of the CIA-triad exposure / ALE engine."""
    model_config = ConfigDict(frozen=True, strict=True)

    confidentiality: float
    integrity: float
    availability: float
    exposure: float
    seg_impact_cr: float
    ale_cr: float


class DomainPriorityResult(BaseModel):
    """One ranked security-domain priority row."""
    model_config = ConfigDict(frozen=True, strict=True)

    domain: str
    t_w: float
    impact_weight: float
    d_priority: float


class ExecutionPayload(BaseModel):
    """Immutable bundle of all deterministic compute results."""
    model_config = ConfigDict(frozen=True, strict=True)

    threat_context: ThreatContext
    epss_prediction: EPSSPrediction
    fair_result: FAIRSimulationResult
    xai_trust: XAITrustResult
    rosi_result: ROSIOptimizationResult
    # Phase-1 extension engines — optional so legacy 5-arg constructions
    # remain valid; populated by _run_core_engines when inputs are supplied.
    business_profile: Optional[BusinessProfileResult] = None
    segment_risk: Optional[SegmentRiskResult] = None
    control_maturity: Optional[ControlMaturityResult] = None
    rosi_v2: Optional[ZRosiResult] = None
    cia_exposure: Optional[CiaExposureResult] = None
    domain_priority: Optional[List[DomainPriorityResult]] = None



# ============================================================================
# SECTION 2: DEVELOPER B — API / UI CONTRACTS (preserved for api_layer)
# These are NOT frozen to allow mutation during request processing
# ============================================================================

class PersonaType(str, Enum):
    BUSINESS = "business"
    TECHNICAL = "technical"


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique conversation session identifier")
    # Optional: when absent, /chat auto-classifies via SemanticIntentRouter;
    # the persona-specific routes default to their own persona.
    persona: Optional[PersonaType] = Field(
        default=None, description="Target persona for response formatting"
    )
    prompt: str = Field(..., description="Natural language user query")
    context_overrides: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional runtime context overrides"
    )


class SlotExtractionResult(BaseModel):
    asset_target: Optional[str] = None
    cve_id: Optional[str] = None
    budget_limit: Optional[float] = Field(default=None, description="Budget limit in INR Lakhs")
    timeline_delta: Optional[int] = Field(default=None, description="Remediation delay in days")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    # Phase-2 NLU extension slots (Task 8) — all optional; engines only run
    # for the slots the user actually supplies (never guessed silently).
    business_unit: Optional[str] = None
    segment_name: Optional[str] = None
    segment_revenue_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    annual_revenue_cr: Optional[float] = None
    sector: Optional[str] = None
    country: Optional[str] = None
    employee_count: Optional[int] = None
    control_maturity: Optional[str] = None
    efficacy_t: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    impact_operational: Optional[float] = Field(default=None, ge=0.0, le=10.0)
    impact_financial: Optional[float] = Field(default=None, ge=0.0, le=10.0)
    risk_w: Optional[float] = Field(default=None, ge=0.0, le=10.0)
    t_w: Optional[float] = Field(default=None, ge=0.0, le=10.0)
    cost_rate: Optional[float] = None
    confidentiality: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    integrity: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    availability: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class AssetNode(BaseModel):
    asset_id: str
    name: str
    criticality_score: float = Field(ge=0.0, le=10.0)
    hardware_replacement_cost_inr_cr: float
    daily_revenue_impact_inr_cr: float
    regulatory_tier: str
    asset_type: str


class EPSSInput(BaseModel):
    cve_id: str
    vendor: Optional[str] = None
    reference_count: int = 0
    tags: List[str] = Field(default_factory=list)
    exploit_poc_published: bool = False
    weaponized: bool = False


class EPSSOutput(BaseModel):
    cve_id: str
    z_score: float
    p_exploit: float = Field(ge=0.0, le=1.0)
    feature_contributions: Dict[str, float]


class FAIRInput(BaseModel):
    asset: AssetNode
    p_exploit: float = Field(ge=0.0, le=1.0)
    susceptibility: float = Field(default=0.8, ge=0.0, le=1.0)
    trial_count: int = Field(default=10000, ge=1000)
    secondary_lef: float = Field(default=0.3, ge=0.0, le=1.0)


class FAIROutput(BaseModel):
    asset_id: str
    cve_id: Optional[str]
    lef: float = Field(ge=0.0, le=1.0)
    primary_loss_inr_cr: float
    secondary_loss_inr_cr: float
    eal_inr_cr: float
    var_95_inr_cr: float
    trial_samples: List[float]


class XAIInput(BaseModel):
    generated_text: str
    reference_text: str
    salient_tokens: List[str]


class XAIOutput(BaseModel):
    trust_score_pct: float = Field(ge=0.0, le=100.0)
    iqr_threshold: float
    flags_status: str
    misaligned_tokens: List[str]


class MILPROSIInput(BaseModel):
    control_cost_inr_cr: float
    eal_inr_cr: float
    risk_reduced_inr_cr: float


class MILPROSIOutput(BaseModel):
    control_cost_inr_cr: float
    risk_reduced_inr_cr: float
    net_capital_saved_inr_cr: float
    rosi_pct: float
    is_economically_viable: bool
    gordon_loeb_ceiling_inr_cr: float


class ComplianceControl(BaseModel):
    control_id: str
    pillar: str
    description: str
    slo_hours: Optional[int] = None
    rbi_category: Optional[str] = None


class DeterministicContextPayload(BaseModel):
    session_id: str
    persona: PersonaType
    timestamp: str
    slots: SlotExtractionResult
    asset: Optional[AssetNode] = None
    epss: Optional[EPSSOutput] = None
    fair: Optional[FAIROutput] = None
    xai: Optional[XAIOutput] = None
    milprosi: Optional[MILPROSIOutput] = None
    compliance_controls: List[ComplianceControl] = Field(default_factory=list)
    guardrail_passed: bool = True
    guardrail_errors: List[str] = Field(default_factory=list)
    # Phase-2: extension engine results surfaced to the API surface
    business_profile: Optional[BusinessProfileResult] = None
    segment_risk: Optional[SegmentRiskResult] = None
    control_maturity: Optional[ControlMaturityResult] = None
    rosi_v2: Optional[ZRosiResult] = None
    cia_exposure: Optional[CiaExposureResult] = None
    domain_priority: Optional[List[DomainPriorityResult]] = None


class ChatResponse(BaseModel):
    session_id: str
    persona: PersonaType
    formatted_output: str
    context_payload: DeterministicContextPayload
    latency_ms: float
