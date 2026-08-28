# Product Requirements Document (PRD)
## Dual-Persona AI Decision Assistant & Cyber Risk Quantification Engine

### Vision
A deterministic Cyber Risk Quantification (CRQ) platform that delivers **mathematically grounded, reproducible** risk metrics to two distinct user personas:
- **Executive View** (Board/CISO/Risk Officer): Monetary exposure (EAL ₹ Cr), ROSI %, Board-level decisions.
- **Technical SOC View** (SOC Lead/DevSecOps): CVSS vectors, EPSS odds, XAI trust tokens, WAF rules, Jira tickets.

### Core Features

#### 1. EPSS Exploit Probability Engine
- 16 Elastic Net logistic coefficients from Jacobs et al. (2021).
- Live Retraining: Incremental SGD learner on streaming intrusion detection telemetry.
- Output: P(Exploit) ∈ [0.0, 1.0] with percentile rank.

#### 2. Open FAIR™ v3.0 Lognormal Monte Carlo Financial Engine
- Loss Event Frequency (LEF) = EPSS × 0.35 susceptibility.
- Primary Loss = (Daily Revenue × 4 days) + (Replacement Cost × 15%).
- Secondary Loss = Primary × Tier Multiplier × 0.80 SLEF.
- 10,000-trial lognormal sampling → EAL (₹ Cr) and 95% VaR.
- **Invariant**: VaR_0.95 > EAL (right-skewed distribution).

#### 3. Explainable AI (XAI) Trust Auditor
- Weighted Cosine Similarity against CVSS definition keywords.
- Adaptive IQR Thresholding (T_IQR = Q3 + σ).
- Mirtaheri et al. (2025) trust formula with α=0.6, β=0.4 weights.
- **Threshold**: EXPERT_GROUNDED ≥ 75%, else UNALIGNED_REVIEW_REQUIRED.

#### 4. MILP 0/1 Knapsack ROSI Optimizer
- Gordon-Loeb (2002) ceiling: Optimal Spend ≤ 0.37 × EAL.
- ROSI % = ((Risk Reduced − Cost) / Cost) × 100.
- Automatic economic viability classification.

#### 5. Continuous Governance
- Automated mapping to SEBI CSCRF 5 Pillars & RBI CSF SLAs.
- Compliance control inventory with SLO hours.

### Target Users
| Persona | Key Metrics | Format |
|---|---|---|
| Business (CISO/Board) | EAL ₹, VaR ₹, Net ROSI, Board Decision | Executive Briefing |
| Technical (SOC/DevSecOps) | EPSS %, XAI Trust %, Jira Ticket, WAF Rules | Diagnostic Console |
