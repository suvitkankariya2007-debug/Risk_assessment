# RiskLens — Cyber Risk Quantification Prototype

A clean HTML/CSS/JavaScript prototype for Problem Statement 26105: AI-Powered Cyber Risk Quantification.

## What is included

1. Executive Overview
   - Financial Exposure
   - Risk Confidence
   - Value-at-Risk
   - Immediate Actions
   - Financial risk trend
   - Top risk contributors
   - Risk reduction opportunities

2. Risk Explorer
   - Select an asset/risk contributor
   - View the evidence behind the financial exposure
   - Trace data back to six simulated source categories
   - Show a data-confidence indicator

3. What-if Simulator
   - Simulate delaying a patch, reducing Multi-Factor Authentication coverage, or delaying network segmentation
   - Adjust delay duration
   - See projected financial exposure change
   - Receive a recommendation

4. Investment Plan
   - Fixed ₹1 crore budget
   - Recommended control portfolio
   - Cost vs estimated risk reduction
   - Explain why the portfolio was selected

## Data note

This is a FRONTEND PROTOTYPE. The displayed values are synthetic demonstration data, not real organizational telemetry or financial claims.

The architecture is intended to represent future connectors to:
- Vulnerability scanners
- Security Information and Event Management systems
- Asset inventory / Configuration Management Database
- Cloud platforms
- Identity and Access Management systems
- Business-impact / financial data

## Run

No installation is required.

Open `index.html` in a browser.

For a local server (recommended):
- VS Code → install/use Live Server, or
- Python: `python -m http.server 5500`
- Open: `http://localhost:5500`

## Planned next step

Connect the same frontend to a FastAPI backend and replace the synthetic JavaScript data with API responses from a normalized risk-data model.
