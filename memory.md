# Memory — What Has Been Done

## Developer A: Core Mathematical Engines Built & Validated

### Files Implemented
- `schemas/data_models.py` — Frozen/strict Pydantic v2 contracts (ThreatContext, EPSSPrediction, FAIRSimulationResult, XAITrustResult, ROSIOptimizationResult, ExecutionPayload).
- `core_engines/topology_graph.py` — Mock Neo4j asset resolver with TIER_1/TIER_2 standardization.
- `core_engines/epss_model.py` — 16-feature Elastic Net logistic model + SGD online learner.
- `core_engines/fair_model.py` — Open FAIR v3.0 lognormal Monte Carlo engine.
- `core_engines/xai_trust.py` — Mirtaheri et al. (2025) trust auditor with trigram cosine similarity.
- `core_engines/rosi_optimizer.py` — Gordon-Loeb ROSI optimizer with lakhs→Cr conversion.
- `tests/test_engines.py` — 5 mandatory invariant tests + bonus coverage.

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
