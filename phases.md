# Phases & Dependencies

## Current Status

| Phase | Scope | Status |
|---|---|---|
| Phase 1: Schema Freeze | `schemas/data_models.py` — Frozen Pydantic v2 contracts | ✅ Complete |
| Phase 2: Core Engines | Developer A deterministic compute + Pytest suite | ✅ Complete |
| Phase 3: API Layer | Developer B — FastAPI routes, NLU, synthesis | 🔲 Pending |

## Component Dependency Graph
```
data_models.py ──────────────────── Independent base contract
     │
     ├── topology_graph.py ──────── Independent (mock Neo4j)
     │
     ├── epss_model.py ──────────── Independent (16 coefficients + SGD)
     │
     ├── fair_model.py ──────────── Depends on: epss_model output (P(Exploit)),
     │                                          topology_graph output (costs, tier)
     │
     ├── xai_trust.py ───────────── Depends on: epss_model salient attributions
     │
     └── rosi_optimizer.py ──────── Depends on: fair_model output (EAL)
```

## Build Order
1. `schemas/data_models.py` — Define all contracts first.
2. `core_engines/topology_graph.py` — Mock asset data.
3. `core_engines/epss_model.py` — Exploit probability engine.
4. `core_engines/fair_model.py` — Monte Carlo financial engine.
5. `core_engines/xai_trust.py` — Trust auditor.
6. `core_engines/rosi_optimizer.py` — Security economics optimizer.
7. `tests/test_engines.py` — Validate all invariants.
