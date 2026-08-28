# Rules & Invariants

## What to Use
- **Pure deterministic math**: All scoring, simulation, and optimization is reproducible Python math.
- **Strict Pydantic v2 frozen models**: `model_config = ConfigDict(frozen=True, strict=True)` on all Developer A contracts.
- **NumPy vectorization**: Monte Carlo sampling, percentile computation, and statistical aggregation.
- **Assertions for invariants**: Hard failures on violated mathematical properties.

## What to Avoid
- ❌ Generative LLM math/scoring (no LLM-generated numbers).
- ❌ Unvalidated dictionaries across module boundaries.
- ❌ Mutable schemas in the compute core.
- ❌ Silent error patchups (e.g., clamping VaR to EAL × 1.05).

## Error Handling & Boundaries

### 1. Lognormal Skewness Invariant
```python
assert var_95_cr > eal_cr  # MUST raise AssertionError if violated
```
If Monte Carlo distribution converges symmetrically, this indicates a bug in the sampling parameters. **Never silently fix.**

### 2. EPSS Probability Bounds
```python
if probability < 0.0 or probability > 1.0:
    raise ValueError(f"EPSS probability {probability} outside [0.0, 1.0]")
```

### 3. Gordon-Loeb Economic Ceiling
```python
is_economically_viable = control_cost_cr <= eal_cr * 0.37
```
Spend exceeding 37% of EAL is flagged as not viable. This is a classification, not an error.

### 4. XAI Trust Alignment
```python
alignment_status = "EXPERT_GROUNDED" if trust_score_pct >= 75.0 else "UNALIGNED_REVIEW_REQUIRED"
```
The 75.0% threshold is fixed. Do not adjust without updating the spec.
