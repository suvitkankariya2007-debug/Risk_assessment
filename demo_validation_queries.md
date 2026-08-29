# BASIS — Live Demo Validation Queries

> **Purpose**: This document contains the **exact natural-language questions** the presenter will type into the BASIS chatbot during the live hackathon demo. Each query is designed to prove that the system dynamically parses free-form text, routes to the correct engine, and returns mathematically grounded results — **without any predefined buttons**.

---

## 1. Business Persona Validation Queries

> These queries test the **Open FAIR™ Monte Carlo** engine, **Gordon-Loeb** economic viability ceiling, and **0/1 Knapsack ROSI Optimizer**.

### Query B1 — Financial Loss Breakdown (Downtime vs. Regulatory Fines)

```
What is the total expected annual financial loss for our Core Payment Switch, 
and how much of that comes from operational downtime versus regulatory penalties?
```

**What to validate in the response:**
- ✅ NLU routes to `POST /api/v1/chat/business` (persona = BUSINESS)
- ✅ Response shows **Expected Annual Loss (EAL) in ₹ Cr** — from FAIR Monte Carlo simulation (10,000 iterations)
- ✅ Response separately breaks down **Primary Loss** (operational downtime at ₹15L/hour) vs. **Secondary Loss** (SEBI/RBI regulatory fines)
- ✅ Response shows **95% Value-at-Risk (VaR)** and confirms `VaR_95 > EAL` (risk invariant)
- ✅ All numbers come from the deterministic `ExecutionPayload` — zero LLM hallucination

---

### Query B2 — Budget Viability via Gordon-Loeb & ROSI

```
Our CISO wants to allocate ₹25 Lakhs for patching the customer database. 
Is this budget economically viable, and what is the return on that security investment?
```

**What to validate in the response:**
- ✅ NLU detects "₹25 Lakhs" via regex → extracts `budget_lakhs = 25.0`
- ✅ NLU detects "customer database" → extracts `asset_name = customer_db`
- ✅ Routes to `POST /api/v1/chat/business` (budget + CISO = business signals)
- ✅ Response includes **ROSI %** = `(Risk_Reduced - Control_Cost) / Control_Cost × 100`
- ✅ Response includes **Gordon-Loeb Capital Ceiling** (≤ 37% of EAL) and states whether the ₹25L spend is **within** or **exceeds** the ceiling
- ✅ Response explicitly states "economically viable" or "NOT economically viable (exceeds Gordon-Loeb ceiling)"

---

### Query B3 — Executive Justification with Monte Carlo Evidence

```
The board is asking whether we should invest 3 Crores in a full network segmentation 
project for the API Gateway. Can you run the financial risk analysis and tell me 
if the expected risk reduction justifies the spend?
```

**What to validate in the response:**
- ✅ NLU detects "3 Crores" → `budget_lakhs = 300.0`
- ✅ NLU detects "API Gateway" → `asset_name = api_gateway`
- ✅ Routes to `POST /api/v1/chat/business` (board + invest + spend = business signals)
- ✅ Response shows EAL, VaR, and compares `Control_Cost (₹3 Cr)` against the **Gordon-Loeb ceiling** — for a high-budget scenario this should flag the spend as potentially exceeding the optimal investment threshold
- ✅ Response includes **Net Benefit (₹ Cr)** = `Risk_Reduced - Control_Cost`
- ✅ Guardrail passes — all currency figures in the response match the `ExecutionPayload`

---

## 2. Technical Persona Validation Queries

> These queries test the **EPSS 16-variable logistic regression** (Jacobs et al.), **XAI Semantic Alignment** (Mirtaheri et al. Integrated Gradients), and **Trust Score** verification.

### Query T1 — Real-World Exploit Probability (EPSS vs. CVSS)

```
What is the real-world exploit probability for CVE-2024-1234 based on the EPSS model, 
and how does it compare to just using the static CVSS score?
```

**What to validate in the response:**
- ✅ NLU detects `CVE-2024-1234` via regex → strong technical signal (+3 weight)
- ✅ Routes to `POST /api/v1/chat/technical` (CVE + exploit + EPSS + CVSS = technical signals)
- ✅ Response shows **EPSS Exploit Probability** as a decimal (e.g., `0.8742` = 87.42%) — NOT a static CVSS ordinal rating
- ✅ Response shows **CVSS Vector** string (e.g., `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`) and Base Score
- ✅ Response includes **EPSS Odds Ratio** = `P / (1 - P)` and **Z-Score** from the 16-feature logistic regression
- ✅ Key differentiator: EPSS uses 16 boolean features (vendor, weaponization, PoC, tags) whereas CVSS is a static vector — the response must surface this distinction

---

### Query T2 — XAI Trust Score & Semantic Alignment

```
Can I trust the risk model's output for the payment server vulnerability? 
Show me the XAI trust score and whether the salient features align with 
the official CVSS vector definition.
```

**What to validate in the response:**
- ✅ NLU routes to `POST /api/v1/chat/technical` (trust score + XAI + salient + CVSS = technical signals)
- ✅ Response shows **XAI Trust Score** as a percentage (e.g., `91.4%`)
- ✅ Response shows **Alignment Status**: `EXPERT_GROUNDED` (if trust ≥ 75%) or `REVIEW_REQUIRED` (if trust < 75%)
- ✅ Response lists **Salient Feature Tokens** (e.g., `[remote, code_execution, unauthenticated]`) — these are the tokens with the highest Integrated Gradient attributions
- ✅ The key proof: salient tokens like "remote" and "code_execution" should semantically match the CVSS vector's `AV:N` (Network = remote) and `C:H/I:H` (High Confidentiality/Integrity = code execution) — this is the Mirtaheri et al. alignment check

---

### Query T3 — Combined Threat Intelligence Deep-Dive

```
Give me the full technical threat assessment for CVE-2024-1234 on our core payment switch, 
including the EPSS exploit odds, the feature contributions from the logistic regression model, 
and whether the XAI Integrated Gradients confirm the model is trustworthy.
```

**What to validate in the response:**
- ✅ NLU detects `CVE-2024-1234` + "EPSS" + "logistic regression" + "XAI" + "Integrated Gradients" = heavy technical routing
- ✅ Routes to `POST /api/v1/chat/technical`
- ✅ Response includes all three subsystems:
  1. **EPSS**: Probability, Odds Ratio, Z-Score
  2. **FAIR**: EAL (₹ Cr), VaR 95% (₹ Cr), Primary vs. Secondary Loss
  3. **XAI**: Trust Score %, Alignment Status, Salient Tokens list
- ✅ Response includes **ROSI viability** assessment even in technical mode
- ✅ Guardrail verification passes — no hallucinated numbers in the output

---

## 3. Edge Case / Mixed Intent Validation

> These queries test the NLU classifier's ability to handle ambiguous or mixed-intent questions.

### Query M1 — Mixed Business + Technical (Should Default to Business)

```
How much money are we losing because of unpatched vulnerabilities, and is our 
current security budget of ₹50 Lakhs enough to cover the top risks?
```

**Expected**: Routes to **BUSINESS** (money + losing + budget + ₹50 Lakhs override technical "vulnerabilities" signal)

---

### Query M2 — Pure Technical with No CVE (Should Still Route Technical)

```
Show me the EPSS exploit probability and XAI trust score for the most 
critical weaponized threat on our infrastructure.
```

**Expected**: Routes to **TECHNICAL** (EPSS + exploit + XAI + trust score + weaponized = 5+ technical signals)

---

## Demo Flow Checklist

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open `basis-prototype.html` in browser | UI loads with empty input field, **NO predefined buttons** |
| 2 | Type Query B1 and press Enter | Response shows EAL, VaR, Primary/Secondary Loss breakdown |
| 3 | Type Query B2 and press Enter | Response shows ROSI %, Gordon-Loeb ceiling, viability assessment |
| 4 | Type Query T1 and press Enter | Response shows EPSS probability, CVSS comparison, odds ratio |
| 5 | Type Query T2 and press Enter | Response shows XAI Trust Score, alignment status, salient tokens |
| 6 | Verify route indicator below input | Shows `⟶ Detected persona: BUSINESS` or `TECHNICAL` dynamically |
| 7 | Verify no hallucinated numbers | All ₹ figures match `ExecutionPayload` (guardrail passes) |
