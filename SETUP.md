# CyberRiskIQ Copilot — Developer Setup Guide

> **Organisation:** SuvitPay Fintech Solutions Pvt Ltd  
> **System:** CyberRiskIQ Copilot — AI-powered Cyber Risk Quantification & Chat  
> **Stack:** Python 3.12 · FastAPI · Vanilla HTML/JS · Google Gemini / Groq LLM

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture at a Glance](#2-architecture-at-a-glance)
3. [Prerequisites](#3-prerequisites)
4. [Repository Structure](#4-repository-structure)
5. [Installation](#5-installation)
6. [API Keys Setup](#6-api-keys-setup)
7. [Running the Application](#7-running-the-application)
8. [Using the Chatbot](#8-using-the-chatbot)
9. [Running Tests](#9-running-tests)
10. [LLM Fallback Chain](#10-llm-fallback-chain)
11. [Uploading a Vulnerability Scan](#11-uploading-a-vulnerability-scan)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Overview

The **CyberRiskIQ Copilot** is a dual-persona AI chatbot for cyber risk quantification. It combines a **deterministic mathematical core** (Open FAIR™, EPSS, Gordon-Loeb, Monte Carlo) with an **LLM synthesis layer** (Gemini/Groq) to deliver:

- **Executive Persona** — Financial exposure, EAL, 95% VaR, ROSI, budget viability in plain English.
- **Technical Persona** — CVE analysis, EPSS exploitability probabilities, XAI trust scores, SecOps remediation priorities.

> **Zero-Hallucination Guarantee:** All financial/risk numbers are calculated deterministically by `core_engines/` and validated by `SanityGuardrailVerifier` *before* reaching the LLM. The LLM only formats prose — it never computes numbers.

---

## 2. Architecture at a Glance

```
Browser (index.html / style.css)
        │  HTTP on port 3000
        ▼
  FastAPI Server (port 8000)
  ├── api_layer/main.py          ← App entry point
  ├── api_layer/dual_routes.py   ← /chat/business  /chat/technical
  ├── api_layer/synthesizer.py   ← LLM prose synthesis
  ├── api_layer/scan_ledger.py   ← In-memory scan upload & lookup
  └── api_layer/guardrails.py    ← SanityGuardrailVerifier
        │
        ▼
  core_engines/                  ← FROZEN deterministic math
  ├── epss_model.py              ← FIRST.org EPSS probability
  ├── fair_model.py              ← Open FAIR™ Monte Carlo
  ├── rosi_optimizer.py          ← Gordon-Loeb ROSI
  ├── xai_trust.py               ← XAI trust score
  └── ...
        │
        ▼
  LLM Synthesis (prose only)
  └── Gemini 3.6 Flash  →  Groq qwen3.8-27b  →  Deterministic fallback
```

---

## 3. Prerequisites

| Tool | Minimum Version | Exact Tested Version | Install |
|------|-----------------|----------------------|---------|
| Python | 3.12 | **3.12.3** | [python.org](https://www.python.org/downloads/) |
| pip | 24+ | 24.x | Bundled with Python |
| Git | any | any | [git-scm.com](https://git-scm.com/) |

> ⚠️ **Python 3.12.x is required.** The system is tested and pinned on 3.12.3. Python 3.11 or 3.13 may work but are not guaranteed.

---

## 4. Repository Structure

```
sih/
├── api_layer/                  # FastAPI backend
│   ├── main.py                 # App factory + CORS
│   ├── dual_routes.py          # Chat endpoints + NLU routing
│   ├── synthesizer.py          # LLM wrapper (Gemini/Groq/OpenAI)
│   ├── scan_ledger.py          # Scan upload & in-memory store
│   ├── guardrails.py           # Anti-hallucination verifier
│   └── mock_kb.py              # Static CVE knowledge base (fallback)
│
├── core_engines/               # Deterministic math (DO NOT modify)
│   ├── epss_model.py           # EPSS exploit probability
│   ├── fair_model.py           # FAIR Monte Carlo risk model
│   ├── rosi_optimizer.py       # Gordon-Loeb ROSI
│   ├── xai_trust.py            # XAI trust auditor
│   └── ...
│
├── schemas/
│   └── data_models.py          # Pydantic v2 frozen schemas
│
├── tests/
│   ├── test_api_layer.py       # API integration tests (8 tests)
│   ├── test_engines.py         # Core engine unit tests (21 tests)
│   └── test_chatbot_edge_cases.py
│
├── tools/
│   └── build_real_scan.py      # Generate realistic scan fixtures
│
├── index.html                  # Single-page frontend UI
├── style.css                   # UI styles
├── requirements.txt            # Python dependencies
├── .env.example                # API key template (copy → .env)
├── real_company_vulnerability_scan.json  # Example scan file
└── SETUP.md                    # This file
```

---

## 5. Installation

### Step 1 — Clone the repository

```bash
git clone https://github.com/suvitkankariya2007/sih.git
cd sih
```

### Step 2 — Create a Python virtual environment

```bash
python3 -m venv .venv
```

Activate it:

```bash
# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

> All packages are **exact-pinned** (`==`) to the tested versions. This guarantees identical latency, NLU accuracy, and numerical output as the reference environment.

### Pinned dependency versions

| Package | Pinned Version | Purpose |
|---------|---------------|---------|
| `fastapi` | 0.115.0 | API framework |
| `uvicorn` | 0.30.6 | ASGI server |
| `pydantic` | 2.13.5 | Schema validation |
| `numpy` | 1.26.4 | Monte Carlo math |
| `scikit-learn` | 1.5.2 | TF-IDF NLU fallback |
| `scipy` | 1.14.1 | Statistical distributions |
| `google-genai` | 2.22.0 | Gemini 3.6 Flash SDK |
| `openai` | 1.91.0 | Groq / OpenAI client |
| `python-multipart` | 0.0.9 | Scan file upload |

---

## 5a. AI Models Reference

The system uses **remote-hosted** models — no local GPU or model download is needed. All inference is done via API call.

| Role | Provider | Model ID | Context Window | Typical Latency |
|------|----------|----------|----------------|-----------------|
| **Primary NLU + Synthesis** | Google Gemini | `gemini-3.6-flash` | 1M tokens | 0.8–1.5 s |
| **Fallback NLU + Synthesis** | Groq | `qwen/qwen3.8-27b` | 32K tokens | 0.3–0.8 s |
| **Optional** | OpenAI | `gpt-4o-mini` | 128K tokens | 1–2 s |

### Latency budget

The system enforces a **2.0-second hard timeout** (`asyncio.wait_for`) on all LLM calls:

```
Total response latency breakdown (typical):
├── NLU Intent Parse      0.3–0.8 s  (Gemini/Groq)
├── Core Engine Math      < 0.05 s   (deterministic, CPU-only)
├── LLM Synthesis         0.5–1.5 s  (Gemini/Groq)
└── Total end-to-end      ~350–610 ms (observed in UI)
```

> If the LLM exceeds 2.0 s, the system **automatically falls back** to the deterministic formatted response — financial metrics are always returned.

### Why Groq is faster than Gemini

Groq runs on custom LPU (Language Processing Unit) silicon — not GPUs. This gives it sub-second inference even for 27B-parameter models. When Gemini's free tier is rate-limited (20 req/day), Groq becomes the faster and effectively unlimited primary provider.

---

## 6. API Keys Setup

The chatbot works in **deterministic-only mode** without any API keys (all financial calculations still run). API keys unlock LLM-formatted conversational responses.

### Step 1 — Copy the template

```bash
cp .env.example .env
```

### Step 2 — Fill in your keys

Open `.env` in your editor:

```env
GEMINI_API_KEY="your-gemini-key"
GROQ_API_KEY="your-groq-key"
```

### Where to get free keys

| Provider | Model Used | Free Tier | Get Key |
|----------|-----------|-----------|---------|
| **Google Gemini** | `gemini-3.6-flash` | 20 req/day | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) |
| **Groq** *(recommended fallback)* | `qwen/qwen3.8-27b` | Generous free tier | [console.groq.com/keys](https://console.groq.com/keys) |

> **Recommended:** Set both keys. Gemini is the primary; Groq auto-activates if Gemini hits its daily quota (20 req/day on free tier).

> ⚠️ **Never commit your `.env` file.** It is listed in `.gitignore`.

---

## 7. Running the Application

You need **two terminal windows** open simultaneously.

### Terminal 1 — Backend API server

```bash
source .venv/bin/activate
uvicorn api_layer.main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### Terminal 2 — Frontend web server

```bash
python3 -m http.server 3000
```

### Open the UI

Navigate to: **http://localhost:3000**

The chatbot UI will load. You should see the Executive/Technical persona toggle, metrics cards, scan upload sidebar, and chat input.

---

## 8. Using the Chatbot

### Persona Modes

| Mode | Button | Best for |
|------|--------|----------|
| **BUSINESS** (Executive) | `B` button | Financial exposure, ROSI, budget viability, board-level summaries |
| **TECHNICAL** (SecOps) | `T` button | CVE details, EPSS probabilities, remediation priorities |

> The two personas have **separate chat histories** — switching personas starts a fresh conversation context.

### Sample Questions (without a scan)

**Executive:**
- *"What is the expected annual loss for `customer_db` if `CVE-2023-44487` is exploited?"*
- *"Is a security budget of ₹30 Lakhs viable for `core_payment_switch`?"*
- *"Explain what ROSI means for our security budget."*

**Technical:**
- *"What is the EPSS exploitability probability for `CVE-2021-44228`?"*
- *"Calculate the technical risk for `legacy-dev-sandbox`."*
- *"Explain how the FAIR model works."*

---

## 11. Uploading a Vulnerability Scan

The copilot can ingest real vulnerability scan exports:

1. Click **"Upload Scan (.json / .csv)"** in the left sidebar.
2. Select a scan file (example: `real_company_vulnerability_scan.json` is included in the repo).
3. Once loaded, the sidebar shows "✓ Scan loaded — N findings."
4. Now ask contextual questions about the scan:

**Executive scan questions:**
- *"Which vulnerabilities pose the highest financial risk to our business?"*
- *"Where should we invest our security budget to handle these vulnerabilities?"*
- *"Summarize the scan findings for the board in monetary terms."*

**Technical scan questions:**
- *"Which CVEs have a published PoC and EPSS > 99%?"*
- *"Give me a prioritized remediation list for all findings by severity."*
- *"Explain CVE-2024-3094 on payment-switch-01."*

### Supported scan formats

| Format | Source | Notes |
|--------|--------|-------|
| `.json` | Any JSON with `cve_id`, `asset_name`, `cvss_score` fields | Flexible field mapping |
| `.csv` | Qualys / Tenable / CrowdStrike export | Headers auto-detected |

---

## 9. Running Tests

```bash
source .venv/bin/activate

# Full test suite
pytest tests/ -v

# API integration tests only (8 tests — requires uvicorn NOT running)
pytest tests/test_api_layer.py -v

# Core engine unit tests (21 tests — pure math, no API needed)
pytest tests/test_engines.py -v
```

Expected output:
```
tests/test_engines.py      21 passed
tests/test_api_layer.py     8 passed
```

---

## 10. LLM Fallback Chain

The system is designed to be **always available** even without API keys:

```
1. Gemini 3.6 Flash       ← Primary (fast, free 20 req/day)
        │ (429 rate-limited or unavailable)
        ▼
2. Groq qwen3.8-27b       ← Fallback (generous free tier, very fast)
        │ (unavailable)
        ▼
3. OpenAI gpt-4o-mini     ← Optional fallback (requires paid key)
        │ (unavailable)
        ▼
4. Deterministic Fallback ← Always works, no API needed
   (returns structured scan summary + computed financial metrics)
```

> The deterministic fallback still returns **accurate EAL, VaR, ROSI** values — just without conversational prose formatting.

---

## 12. Troubleshooting

### "Could not reach the API server"
- Ensure `uvicorn` is running on port 8000.
- Check for import errors in the uvicorn terminal.

### LLM returns generic/fallback response
- Check that `.env` exists and API keys are correctly quoted.
- Gemini free tier: 20 requests/day. If exhausted, add a Groq key.
- Verify key validity: `gsk_...` for Groq, `AI...` for Gemini.

### "429 RESOURCE_EXHAUSTED" in terminal
- Gemini daily quota hit. Groq will auto-activate if `GROQ_API_KEY` is set.

### "model decommissioned" error
- The Groq model name may have changed. Check [console.groq.com/docs/deprecations](https://console.groq.com/docs/deprecations) and update `dual_routes.py` and `synthesizer.py`.

### Scan upload not reflected in answers
- Ensure the file uploaded successfully (sidebar shows "✓ Scan loaded").
- Check that your questions reference the scan context (e.g., "from the uploaded scan...").

### Tests fail with import errors
- Ensure the virtual environment is activated: `source .venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Recommended | Google Gemini API key for NLU + synthesis |
| `GROQ_API_KEY` | Recommended | Groq API key for fallback LLM (free, fast) |
| `OPENAI_API_KEY` | Optional | OpenAI fallback (paid) |
| `LLM_PROVIDER` | Optional | Force a provider: `gemini`, `groq`, `openai` |

---

*Built for Smart India Hackathon 2026 · CyberRiskIQ by SuvitPay Fintech Solutions*
