# CyberRiskIQ Copilot

CyberRiskIQ Copilot is a hybrid AI/deterministic cyber risk quantification and diagnostics platform. It provides persona-driven chat capabilities, automated vulnerability scan file ingestion, and a robust math core powered by Open FAIR™ v3.0, EPSS, XAI Trust, and Gordon-Loeb economic optimization.

---

## Getting Started

### Prerequisites
- Python 3.10+
- A valid `GEMINI_API_KEY` configured in a `.env` file in the project root:
  ```env
  GEMINI_API_KEY=your_gemini_api_key_here
  ```

---

## How to Run

### 1. Set Up the Virtual Environment
Create and activate the virtual environment, then install the required dependencies:
```bash
# Navigate to the workspace
cd /home/suvitk/sih

# Create/Verify Virtual Environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Start the Backend API Server
Start the FastAPI server utilizing Uvicorn:
```bash
# Ensure you are in the workspace and virtual environment is active
source .venv/bin/activate
uvicorn api_layer.main:app --reload --port 8000
```
*The API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).*

### 3. Start the Frontend User Interface
Start a local HTTP server to serve the static frontend chat interface:
```bash
# Open a new terminal and run:
cd /home/suvitk/sih
python -m http.server 3000
```
Open [http://localhost:3000/index.html](http://localhost:3000/index.html) in your browser to interact with the CyberRiskIQ Copilot.

---

## Running the Test Suite

Run the full automated test suite to verify the system integrity, NLU routing, and mathematical engines:

```bash
# Run all unit, integration, and edge-case stress tests (46 tests)
pytest tests/ -v

# Run only core mathematical engine tests
pytest tests/test_engines.py -v

# Run only API integration routes tests
pytest tests/test_api_layer.py -v

# Run only edge-case stress tests
pytest tests/test_chatbot_edge_cases.py -v
```

---

## Core Features
1. **Business Persona**: Executive-level summaries focusing on financial risk metrics (VaR, EAL) and ROI, strictly adhering to the **Zero Math Rule** (the LLM formats pre-calculated inputs and does not compute math).
2. **Technical Persona**: SecOps-oriented diagnostics showing CVEs, CVSS scores, threat indicator details, and remediation steps.
3. **Vulnerability Scan Ingestion**: Import Tenable/Qualys/CrowdStrike scans directly through the UI sidebar to dynamically evaluate live risks across the asset network.
4. **Offline Fallback Routing**: Robust intent extraction handles rate limits and offline LLMs gracefully, using deterministic rules to continue routing scan analysis and general knowledge questions.
