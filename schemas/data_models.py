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


class ExecutionPayload(BaseModel):
    """Immutable bundle of all deterministic compute results."""
    model_config = ConfigDict(frozen=True, strict=True)

    threat_context: ThreatContext
    epss_prediction: EPSSPrediction
    fair_result: FAIRSimulationResult
    xai_trust: XAITrustResult
    rosi_result: ROSIOptimizationResult


# ============================================================================
# SECTION 2: DEVELOPER B — API / UI CONTRACTS (preserved for api_layer)
# These are NOT frozen to allow mutation during request processing
# ============================================================================

class PersonaType(str, Enum):
    BUSINESS = "business"
    TECHNICAL = "technical"


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique conversation session identifier")
    persona: PersonaType = Field(..., description="Target persona for response formatting")
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


class ChatResponse(BaseModel):
    session_id: str
    persona: PersonaType
    formatted_output: str
    context_payload: DeterministicContextPayload
    latency_ms: float
