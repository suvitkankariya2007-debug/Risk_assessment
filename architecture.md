# Architecture
## 5-Tier Architecture & Data Flow

### Tier Overview
```
1. Dual-Persona Interaction Layer (UI)
   └─→ 2. Gateway, NLU & State Management (FastAPI)
         └─→ 3. Continuous Real-Time Retraining Bus
         └─→ 4. Deterministic Scientific Compute Core ← Developer A
               └─→ 5. Synthesis, Economic Sanity Bounds & Outputs
```

### Tier 4: Deterministic Compute Core (Developer A Scope)
```
crq_backend/
├── schemas/
│   └── data_models.py           # Frozen Pydantic v2 contracts
├── core_engines/
│   ├── topology_graph.py         # Mock Neo4j asset resolver
│   ├── epss_model.py             # 16 Elastic Net + SGD online learner
│   ├── fair_model.py             # Open FAIR v3.0 Monte Carlo engine
│   ├── xai_trust.py              # Mirtaheri et al. (2025) trust auditor
│   └── rosi_optimizer.py         # Gordon-Loeb ROSI optimizer
├── api_layer/                    # Developer B scope (excluded)
│   ├── dual_routes.py
│   ├── synthesizer.py
│   └── guardrails.py
└── tests/
    └── test_engines.py           # Automated invariant verification
```

### Data Flow
```
P(Exploit) ──→ FAIR Engine ──→ EAL/VaR ──→ ROSI Optimizer
                  ↑                              ↓
Asset Topology ───┘                    Gordon-Loeb Viability
                                              ↓
EPSS Salient Attributions ──→ XAI Trust Auditor
```

### Tech Stack
| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| Schemas | Pydantic v2 (frozen, strict) |
| Numerics | NumPy, SciPy |
| Online Learning | Scikit-Learn SGDClassifier |
| Testing | Pytest |
| Graph Store | Mock Neo4j (in-memory dict) |
