# Memory — What Has Been Done

## System Status
- **Build State**: CLEAN & STABLE
- **Directory Structure**: Strictly enforced. Untracked root files migrated into `api_layer/` and `core_engines/`.
- **Test Suite Pass Rate**: 21/21 passing tests (`pytest tests/test_engines.py`).
- **Deterministic Core**: Fully protected and frozen.

## Deduplication Audit
- Removed redundant copy artifacts from root: `main (copy).py`, `requirements (copy).txt`, `README(2).md`, `README(3).md`, `__init__(1..3).py`, `data_models.py`, `epss_model.py`, `fair_model.py`, `rosi_optimizer.py`, `topology_graph.py`, `xai_trust.py`, `synthesizer.py`, `test_engines.py`, `core_engines/retraining_bus.py`, `__pycache__`, and `.pytest_cache`.
- Single source of truth established for original `README.md`, `schemas/data_models.py`, `core_engines/*`, and `api_layer/*`.

## API Contract Map
- `POST /api/v1/chat/business`: Executes core math engines, generates locked `ExecutionPayload`, calls `format_business_briefing()`, verifies financial integrity via `SanityGuardrailVerifier`, and returns `ChatResponse`.
- `POST /api/v1/chat/technical`: Executes core math engines, calls `format_technical_diagnostic()`, verifies via `verify_financial_integrity()`, and returns `ChatResponse`.
- `POST /api/v1/models/stream-update`: Ingests real-time telemetry batches for SGD online retraining via `EPSSPredictor.continuous_online_update()`.
- `GET /health`: Healthcheck endpoint for CyberRiskIQ Gateway.

## Next Steps
- Populate `.env` with live external LLM API keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`) and set `LLM_PROVIDER` for dynamic synthesis.
- Connect Kafka/event-stream consumers directly to `POST /api/v1/models/stream-update`.
- Wire frontend UI components (`index.html`) to `/api/v1/chat/business` and `/api/v1/chat/technical`.

---

## Developer A: Core Mathematical Engines Built & Validated

### Files Implemented
- `schemas/data_models.py` — Frozen/strict Pydantic v2 contracts (ThreatContext, EPSSPrediction, FAIRSimulationResult, XAITrustResult, ROSIOptimizationResult, ExecutionPayload).
- `core_engines/topology_graph.py` — Mock Neo4j asset resolver with TIER_1/TIER_2 standardization.
- `core_engines/epss_model.py` — 16-feature Elastic Net logistic model + SGD online learner (`EPSSPredictor`).
- `core_engines/fair_model.py` — Open FAIR v3.0 lognormal Monte Carlo engine (`FAIRRiskEngine`).
- `core_engines/xai_trust.py` — Mirtaheri et al. (2025) trust auditor with trigram cosine similarity (`XAITrustAuditor`).
- `core_engines/rosi_optimizer.py` — Gordon-Loeb ROSI optimizer (`ROSIOptimizer`).
- `tests/test_engines.py` — 5 mandatory invariant tests + bonus coverage (21/21 passing).

---

## Formula Cheat Sheet

### Open FAIR v3.0
```
LEF = EPSS_prob × 0.35
Primary Loss = (Daily Revenue × 4.0) + (Asset Replacement Cost × 0.15)
Secondary Loss = Primary × (2.5 if TIER_1_CRITICAL else 1.2) × 0.80
Scale = (Primary + Secondary) × LEF
Sample = Lognormal(ln(max(0.01, Scale)), sigma=0.85)
EAL = mean(samples)
VaR_0.95 = percentile(samples, 95)
INVARIANT: VaR_0.95 > EAL
```

### EPSS (Jacobs et al., 2021)
```
z = -6.18 + Σ(βᵢ × Xᵢ)
P(Exploit) = 1 / (1 + exp(-z))

Coefficients:
  vend_microsoft: +2.44    vend_ibm: +2.07        exp_weaponized: +2.00
  vend_adobe: +1.91        vend_hp: +1.62          exp_poc_published: +1.50
  vend_apache: +1.10       ref_count_log: 1.01×ln(1+N)
  tag_code_execution: +0.57  tag_remote: +0.23     tag_dos: +0.22
  tag_web: +0.06           tag_memory_corruption: -0.20
  tag_local: -0.63         vend_google: -0.89      vend_apple: -1.92
```

### XAI Trust (Mirtaheri et al., 2025)
```
T_IQR = Q3 + σ (Adaptive IQR Threshold)
Trust = (α × S_t + β × S_all × (1 − δ_t / δ_all)) × 100
  where α = 0.6, β = 0.4
  S_t = mean similarity of salient tokens
  S_all = mean similarity of all description tokens
  δ_t = std dev of salient, δ_all = std dev of all
Status: EXPERT_GROUNDED if Trust ≥ 75% else UNALIGNED_REVIEW_REQUIRED
```

### Gordon-Loeb (2002)
```
Optimal Security Spend ≤ (1/e) × EAL ≈ 0.37 × EAL
ROSI % = ((Risk Reduced − Control Cost) / Control Cost) × 100
is_economically_viable = (Control Cost ≤ 0.37 × EAL)
```
