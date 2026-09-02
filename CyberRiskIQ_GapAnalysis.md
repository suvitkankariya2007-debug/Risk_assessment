# CyberRiskIQ Copilot — Risk-Quantification Gap Analysis & Build Brief

> **For Cline / Antigravity agent:** this file is self-contained. No external
> document needs to be attached or referenced. Every formula, constant, and
> constraint is spelled out below. Jump straight to
> [Section 8 — Build Prompt](#8-build-prompt) if you just need the task list.

---

## 1. Full Gap Analysis — Missing Risk-Quantification Components

Scope: entire system (compute engines + chatbot). Priority reflects how
central the gap is to giving Technical + Economic + Legal (TEL) coverage.

| Risk-Quant Component | Status in CyberRiskIQ | What's Missing | Formula | Priority |
|---|---|---|---|---|
| Business Analysis module (business units, segments, revenue-weighting) | NOT PRESENT — `AssetTopologyGraph` only stores asset tier/dependency, no revenue-per-segment or business-unit hierarchy | Segment definition step; % of revenue per segment/unit | n/a (data model) | **High** |
| Segment financial impact | NOT PRESENT — FAIR engine computes EAL/VaR from daily revenue + replacement cost only, not per-segment | Segment-level $ impact breakdown output | `SegImpact = SegRevenue x Impact_w` | **High** |
| Segment actual risk | NOT PRESENT | Actual (not worst-case) segment risk figure | `SegRisk = SegImpact x (Impact_w x Risk_w)` | Medium |
| Domain prioritization | NOT PRESENT — no output ranks which security domain to fund first | Domain-priority ranking in the technical/executive response | `D_priority = T_w x (alpha + Impact_w)` | Medium |
| Control maturity multipliers (Not Implemented → Optimized, 1.25 → 0.25) | NOT PRESENT — CVSS/controls are hardcoded defaults (`base_score=9.8`), no maturity input | Maturity slot in NLU + control-efficacy formula | `ControlEfficacy_T = Efficacy_T x (1.25 - MaturityLevel)` | **High** |
| Cost-adjusted ROSI (adds control efficacy + cost rate) | PARTIAL — `rosi_optimizer.py` implements classic Gordon-Loeb/ROSI (0.37×EAL cap), not the cost-adjusted extension | CostRate + ControlEfficacy terms in the ROSI formula | `Z_ROSI = ((ALE x ControlEfficacy) - (ControlCost x CostRate)) / (ControlCost x CostRate)` | Medium |
| CIA-based exposure and annual loss | NOT PRESENT — `xai_trust.py` computes AI-explanation trust %, unrelated to CIA-triad security posture | A genuine CIA-based exposure engine feeding ALE | `Exposure = 1 - avg(CIA)`; `ALE = Exposure x SegImpact` | **High** |
| Legal / Compliance dimension | NOT PRESENT — no compliance-standard mapping (ISO 27005 / NIST / SCF) in any engine | Compliance-control lookup + regulatory-penalty term in EAL | n/a (data model + lookup) | **High** |
| Business-profile → threat/impact database | PARTIAL — `mock_kb.py` is a static CVE/vuln lookup only, not a business-profile-to-impact mapping | Sector/country/size-aware threat-impact mapping table | n/a (data model) | Medium |
| EPSS real percentile | PARTIAL/APPROXIMATED — assumes population `z~N(-6.18,2.5)` instead of a live percentile | Live call to the FIRST.org EPSS API for calibrated percentile | n/a (external API call) | Medium |

---

## 2. Chatbot-Layer-Only Comparison

Scope restricted to `api_layer/` (NLU, routing, templates, guardrails) — no
changes to `core_engines/` math. Use this table for conversational/UX fixes
without touching the frozen compute core.

| Chatbot Layer Feature | Current Behavior | Gap | Chatbot-Only Fix |
|---|---|---|---|
| NLU slot extraction (`_extract_slots`) | Extracts CVE id, INR budget, asset name only | No segment/business-unit, control-maturity, or CIA slots | Add regex/LLM slots: `business_unit`, `segment_name`, `segment_revenue_pct`, `control_maturity` (enum), `cia_weights` |
| Intent routing (`_analyze_query_intent`) | 5 intents: UNIDENTIFIED, CONVERSATIONAL, GENERAL_KNOWLEDGE, SCAN_ANALYSIS, RISK_QUANTIFICATION | No `COMPLIANCE_CHECK` or `SEGMENT_PRIORITIZATION` intent | Add 2 intents routing to (once built) compliance + domain-priority engines, keeping Zero-Math rule intact |
| Executive template (`format_business_briefing`) | Emits raw metric labels: `"EAL INR X Cr, VaR_95 INR Y Cr, ROSI Z%, Gordon-Loeb viable: Y/N"` | Too technical for a board persona | Rewrite to plain business language (see [Section 3](#3-executive-persona-language-problem)) — Zero-Math stays, only wording changes |
| Technical template (`format_technical_diagnostic`) | CVSS vector, EPSS %, XAI trust % — appropriate for SOC persona | None — correctly scoped | No change needed |
| Conversational concept answers | Static explanations for ROSI/EPSS/FAIR/Gordon-Loeb only | No explanation for new terms (SegImpact, cost-adjusted ROSI, Domain Priority) | Extend `generate_conversational_response` concept dictionary |
| Guardrail (`SanityGuardrailVerifier`) | Regex-checks INR Cr/Lakhs and NN.NN% against payload; Gordon-Loeb contradiction check | No check for new Legal/compliance claims or segment-level figures | Extend guardrail regex set + payload cross-check; keep fail-open-to-flag behavior |

---

## 3. Executive-Persona Language Problem

Current output (`format_business_briefing`) is metric-dense and assumes
board members know VaR, EAL, and Gordon-Loeb terminology:

> `"EAL INR 4.2 Cr, VaR_95 INR 7.8 Cr, ROSI 62%, Gordon-Loeb viable: Yes (cap INR 1.55 Cr)"`

**Recommended reframe** — same numbers, same Zero-Math rule, only wording changes:

> "On average, a successful attack on this system could cost the business
> about INR 4.2 crore a year. In a bad-case scenario, that could rise to
> roughly INR 7.8 crore."
>
> "Spending on the recommended control is expected to return about INR 0.62
> for every INR 1 invested — and it stays within the INR 1.55 crore
> threshold we'd consider cost-justified."

**Enforced rule, not a style preference:** zero unexplained acronyms — `VaR`,
`EAL`, `ALE`, `ROSI`, `Z-ROSI`, `CIA`, `SegImpact`, `D_priority` — may appear
as literal tokens in the business/executive persona output. Every one gets
translated into a plain phrase. This is a hard requirement in
[Section 8](#8-build-prompt), Task 9, with a banned-token lint check, not a
suggestion.

Implementation note: this is a template-wording change only, inside
`format_business_briefing` / `template_business_briefing` — no engine,
schema, or guardrail-regex change needed, since the guardrail already
tolerance-matches numbers regardless of surrounding prose.

---

## 4. Latency Budget

New engines and any optional local model must not slow the chatbot down.

- All new formula modules (`business_profile`, `segment_risk`,
  `control_maturity`, `rosi_v2`, `cia_exposure`, `domain_priority`) are pure
  arithmetic — target well under **10ms** each.
- Any model used stays a **warm singleton loaded once at startup** — never
  reloaded per-request.
- The new FIRST.org EPSS API call gets a **2-second timeout** with fallback
  to the existing offline approximation — a slow external API must never
  block the chat response.
- The new scan-data persistence layer must not add a synchronous disk
  round-trip to the hot request path — reads for an in-flight request hit
  an in-memory cache first.
- **End-to-end target:** a request needing only the new formula math (no
  EPSS call, no model call) returns in well under **200ms** total.

---

## 5. CPU-Only, Low-Disk Model Options

Scope-limited on purpose: no GPU assumption, smallest viable disk footprint.
These are **optional** upgrades for the local synthesis/formatting step
only — not required for the risk-quantification build in
[Section 8](#8-build-prompt), which is pure Python with no model changes.

| Model | Params / Disk (Q4 GGUF) | Role | Why it fits a CPU-only, low-disk box | Link |
|---|---|---|---|---|
| Qwen2.5-0.5B-Instruct | 0.5B, ~350 MB | Local synthesis (Zero-Math JSON→prose formatter) | Smallest instruction-tuned model that reliably follows structured-output prompts; runs comfortably on a laptop CPU with no GPU; lowest disk footprint of any viable option | https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct |
| Qwen2.5-1.5B-Instruct | 1.5B, ~1.0 GB | Fallback / higher-quality formatter | Still CPU-friendly (a few seconds per response on a modern CPU); use only if the 0.5B model's phrasing quality isn't sufficient | https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct |
| TinyLlama-1.1B-Chat-v1.0 | 1.1B, ~0.6 GB | Alternative lightweight formatter | Apache 2.0, purpose-built for constrained/edge hardware; smaller disk footprint than the 1.5B option at similar quality | https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0 |
| all-MiniLM-L6-v2 | 22M, ~90 MB | Embeddings for intent/persona routing | Already the right size class for CPU-only use; keep as-is for the routing layer, no change needed | https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2 |

---

## 6. Overall Assessment

The architecture is well ahead on engineering rigor — frozen contracts,
guardrails, fallback ladders, and online EPSS retraining are solid
foundations. Where it currently falls short is **coverage, not quality**:
the system quantifies Technical + partial Economic risk (FAIR/EPSS/ROSI)
but has no Legal/compliance dimension, no segment/business-unit revenue
weighting, and no control-maturity scoring. The gaps in
[Section 1](#1-full-gap-analysis--missing-risk-quantification-components)
are additive: each can be built as a new `core_engines/` module feeding the
existing `ExecutionPayload`, without breaking the frozen-contract design.

---

## 7. Will Uploading Real Company Vulnerability Files Actually Work?

**Short answer: partially.** Ingestion and CVE lookup work, but the compute
engines currently override real data with hardcoded demo placeholders
before the numbers ever reach the chatbot — so uploading a real scan today
produces a plausible-looking but not-actually-grounded answer.

| Pipeline Stage | What Happens With a Real Uploaded Scan File | File / Function to Fix |
|---|---|---|
| Scan ingestion | **WORKS** — Qualys/Tenable/CrowdStrike JSON/CSV is normalized into `ScanFinding` records in `scan_ledger` | `api_layer/scan_ledger.py` (no fix needed) |
| CVE lookup | **WORKS** — `scan_ledger.lookup_cve()` is checked before `mock_kb`, so an uploaded CVE is found first | `api_layer/dual_routes.py` (no fix needed) |
| CVSS severity | **BROKEN** — `_run_core_engines` injects a hardcoded `cvss_base_score=9.8` and fixed vector for every request | `api_layer/dual_routes.py` → `_run_core_engines()` |
| Asset resolution | **BROKEN** — an uploaded asset name that doesn't exactly match/substring-match a hardcoded key silently falls back to the demo asset `core_payment_switch` | `core_engines/topology_graph.py` + `AssetTopologyGraph` seed data |
| EPSS probability | **APPROXIMATED** — uses an assumed population `z~N(-6.18, 2.5)` instead of the real per-CVE percentile from FIRST.org | `core_engines/epss_model.py` |
| Persistence | **BROKEN** — `scan_ledger` and all engine singletons are in-memory only; uploaded data is lost on every server restart | `api_layer/scan_ledger.py` (needs a persistence layer) |

This is the **highest-priority fix** for production use, since it silently
defeats the entire point of scan upload without raising any error — the
guardrail only checks arithmetic consistency against `ExecutionPayload`, not
whether `ExecutionPayload` itself reflects the uploaded file. This is why
Phase 0 below comes before any new formula work.

---

## 8. Build Prompt

Fully self-contained — paste the block below directly into the agent's
task/chat panel. No external document needs to be attached or referenced.
**Model changes are explicitly out of scope.**

```
ROLE: You are extending the CyberRiskIQ Copilot repo (FastAPI + frozen
Pydantic core_engines/ + api_layer/). Read architecture.md, rules.md,
phases.md, and schemas/data_models.py in this repo before writing any code.
Do not reference or assume access to any external paper or document —
every formula and value you need is given in full below.

SCOPE LOCK: Do not add, swap, or recommend any new LLM/model. The synthesis
layer stays exactly as it is. This task is pure deterministic Python — new
calculation modules in core_engines/, no model changes anywhere.

===========================================================
PHASE 0 -- FIX BEFORE ANYTHING ELSE (real data currently gets overridden)
===========================================================
Today, uploading a real vulnerability scan file does NOT actually drive
the output -- these four hardcodes silently override it:

a. api_layer/dual_routes.py, function _run_core_engines():
   Currently injects cvss_base_score=9.8 and a fixed CVSS vector for
   every request.
   FIX: read the real score/vector from the matched ScanFinding (from
   scan_ledger) when one exists. Only use 9.8 as a fallback when no
   uploaded scan data matches.

b. core_engines/topology_graph.py (AssetTopologyGraph):
   Currently, an asset name that doesn't exactly match/substring-match a
   hardcoded key silently falls back to the demo asset
   "core_payment_switch".
   FIX: make unmatched assets return an explicit UNRESOLVED_ASSET state
   instead of silently substituting a fake asset. Let the caller decide:
   prompt the user for the asset's business context, or proceed with a
   generic unweighted profile -- never silently mislabel it as a
   different real asset.

c. api_layer/scan_ledger.py:
   Currently in-memory only -- all uploaded scan data is lost on every
   restart.
   FIX: add a persistence layer (SQLite file is fine) so uploaded
   findings survive a restart.

d. core_engines/epss_model.py:
   Currently approximates exploit probability from an assumed population
   z ~ N(-6.18, 2.5) instead of the real per-CVE percentile.
   FIX: call the real FIRST.org EPSS API
   (https://api.first.org/data/v1/epss?cve=CVE-XXXX-XXXXX) for the
   matched CVE; keep the current approximation only as an offline
   fallback if the API call fails.

ACCEPTANCE TEST FOR PHASE 0: Upload a scan file with a CVE and asset name
that do NOT match any hardcoded default, and show that the EAL/VaR output
actually changes based on that file -- not the demo numbers. Do not
proceed to Phase 1 until this passes.

===========================================================
PHASE 1 -- NEW RISK-QUANTIFICATION MODULES (self-contained formulas)
===========================================================
HARD RULES:
- All new financial/risk numbers must be computed in core_engines/, never
  in the LLM synthesis layer (Zero-Math Rule -- same as the existing
  FAIR/EPSS engines).
- Implement EXACTLY the formulas below. Do not invent variations or add
  terms.
- If an input value isn't derivable from the existing schema, STOP and
  ask me -- never default or guess it silently.
- Every new engine uses the same frozen Pydantic contract + hard
  AssertionError invariant style as core_engines/fair_model.py -- no
  silent clamping.

1. core_engines/business_profile.py
   New objects:
   - BusinessUnit: name (str), sector (str), country (str),
     employee_count (int, optional)
   - Segment: name (str), parent_business_unit (str), revenue_pct
     (float, 0-100), description (str, optional)
   These sit alongside AssetTopologyGraph (compose, don't replace it) --
   an Asset can optionally reference a Segment.

2. core_engines/segment_risk.py
   - Impact_w = Impact_Operational * Impact_Financial
     (Impact_Operational and Impact_Financial are each floats 0-10, one
     per threat/CVE, supplied by caller or looked up from scan data --
     not invented by this module)
   - SegImpact = SegRevenue * Impact_w
     (SegRevenue = segment.revenue_pct/100 * business_unit annual
     revenue, an input)
   - SegRisk = SegImpact * (Impact_w * Risk_w)
     (Risk_w = float 0-10 representing likelihood/success-rate of the
     threat, an input)

3. core_engines/control_maturity.py
   Six fixed multipliers (exact values, do not alter):
     Not Implemented = 1.25
     Initial          = 0.65
     Repeatable       = 0.55
     Defined          = 0.45
     Managed          = 0.31
     Optimized        = 0.25
   Formula: ControlEfficacy_T = Efficacy_T * (1.25 - MaturityLevel)
     (Efficacy_T = float 0-1, the control's nominal/promised efficacy
     against threat T, an input; MaturityLevel = one of the six
     multipliers above)

4. core_engines/rosi_v2.py (add alongside existing rosi_optimizer.py --
   do not remove the original Gordon-Loeb ROSI, expose both)
   Z_ROSI = ((ALE * ControlEfficacy) - (ControlCost * CostRate)) /
            (ControlCost * CostRate)
     (ALE from module 5 below; ControlEfficacy from module 3;
     ControlCost = float, input; CostRate = float, a cost-adjustment
     input e.g. annualization factor -- ask me for its expected range if
     not already defined in the repo)

5. core_engines/cia_exposure.py
   - Exposure = 1 - avg(CIA)
     (CIA = average of three floats 0-1: Confidentiality, Integrity,
     Availability scores derived from current controls -- replace the
     hardcoded z_score=-1.5 placeholder noted in architecture.md
     Section 11.3 with this real computed value wherever that
     placeholder is currently used)
   - ALE = Exposure * SegImpact

6. core_engines/domain_priority.py
   D_priority = T_w * (alpha + Impact_Weight)
     (T_w = float 0-10, how relevant a threat is to a given security
     domain, input; alpha = normalization constant, default 1.0 unless
     told otherwise; Impact_Weight = Impact_w from module 2, normalized
     0-1)
   Domain list -- PROPOSED DEFAULT (a standard NIST-CSF-aligned set --
   replace with your own list if you already have one elsewhere in the
   repo, otherwise use this):
     Identity & Access Management, Endpoint Protection, Network
     Security, Data Protection & Encryption, Email & Messaging Security,
     Cloud Security, Application Security, Vulnerability Management,
     Security Monitoring & Logging, Incident Response, Backup &
     Recovery, Third-Party/Vendor Risk, Security Awareness & Training,
     Governance/Risk/Compliance, Physical Security.

===========================================================
PHASE 2 -- WIRE INTO EXISTING SCHEMA + API + CHAT LAYER
===========================================================
7. Extend schemas/data_models.py with frozen models for each new
   engine's output (BusinessProfileResult, SegmentRiskResult,
   ControlMaturityResult, ZRosiResult, CiaExposureResult,
   DomainPriorityResult) and fold them into ExecutionPayload.

8. Update api_layer/dual_routes.py _extract_slots() to capture new
   slots: business_unit, segment_name, segment_revenue_pct,
   control_maturity (must be one of the six enum values above),
   cia_weights (optional).

9. Update api_layer/synthesizer.py templates:
   - Business/executive persona: FULL LAYMAN LANGUAGE, not just "less
     jargon". Rules:
     * Never output a raw metric label + number with no sentence around
       it (e.g. never just "EAL: INR 4.2 Cr" standing alone).
     * Every number must sit inside a plain sentence describing what it
       means in business terms -- money at risk, likely vs worst-case,
       whether a spend is worth it.
     * Zero unexplained acronyms: VaR, EAL, ALE, ROSI, Z-ROSI, CIA,
       SegImpact, D_priority must NEVER appear as literal tokens in the
       executive/business persona output -- translate each into a plain
       phrase (e.g. "potential yearly loss" instead of "EAL", "a
       bad-case scenario" instead of "VaR_95").
     * Target reading level: a business owner with no security
       background should understand the full answer without looking
       anything up.
     * Technical persona is exempt from all of the above -- keep full
       jargon/precision there, no change to tone.
   - Add a synthesizer-level lint/check (simple regex list of banned
     tokens above) that runs on the business-persona output before it's
     returned, and rewrites/flags if a banned token slipped through.

10. Extend api_layer/guardrails.py regex/tolerance checks to cover every
    new numeric field (SegImpact, SegRisk, Z_ROSI, Exposure, ALE,
    D_priority).

11. Write pytest cases in tests/test_engines.py for each new formula as
    property-based invariants, e.g.:
    - SegRisk <= SegImpact always
    - Exposure is always in [0, 1]
    - ControlEfficacy_T is always in [0, 1.25]

12. Update architecture.md, rules.md, memory.md describing exactly what
    changed, which files, and why -- so future sessions don't need this
    prompt re-explained.

===========================================================
PHASE 3 -- LATENCY BUDGET (must hold for every task above)
===========================================================
13. Performance constraints -- apply to every new module and every
    change to existing ones:
    - All Phase 1 formulas (business_profile, segment_risk,
      control_maturity, rosi_v2, cia_exposure, domain_priority) are pure
      arithmetic on Pydantic models. Each must run in well under 10ms;
      if any implementation needs a loop over more than a few hundred
      items or does any I/O, stop and flag it to me instead of shipping
      it.
    - No model (LLM/embedding) may be loaded per-request. Any model used
      stays a warm singleton loaded once at process startup, same
      pattern as the existing embedding/synthesis models -- reloading
      per-request is not acceptable latency.
    - The new FIRST.org EPSS API call (Phase 0, item d) is a network
      call: wrap it with a short timeout (2s) and a fallback to the
      existing offline approximation if it doesn't return in time -- a
      slow external API must never block or slow down the chat
      response.
    - The new persistence layer (Phase 0, item c) must not add a
      synchronous disk round-trip to the hot request path; write-through
      or async-write patterns are acceptable, but reads for an in-flight
      request should hit an in-memory cache first.
    - End-to-end target: a request that only needs Phase 1 math (no EPSS
      call, no model call) should return in well under 200ms total. A
      request that needs a fresh EPSS lookup can take longer but must
      respect the 2s API timeout above.
    - If any new code path risks breaking these budgets, stop and tell
      me the tradeoff instead of silently shipping something slow.

DELIVERABLE: a diff/PR description listing every file touched, every
formula implemented, and any open question you had to stop and ask me
about instead of guessing.
```

---

## Quick Reference — All External Links

| Purpose | Link |
|---|---|
| EPSS API (live per-CVE exploit percentile) | https://api.first.org/data/v1/epss?cve=CVE-XXXX-XXXXX |
| EPSS API documentation | https://www.first.org/epss/api |
| Qwen2.5-0.5B-Instruct | https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct |
| Qwen2.5-1.5B-Instruct | https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct |
| TinyLlama-1.1B-Chat-v1.0 | https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0 |
| all-MiniLM-L6-v2 | https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2 |
