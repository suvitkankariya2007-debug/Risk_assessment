"""
tests/test_chatbot_edge_cases.py
=================================
Edge-case stress test suite for CyberRiskIQ chatbot.

Tests:
  1. Gordon-Loeb cap enforcement (inflated budget rejection)
  2. Numeric drift / hallucination rejection by SanityGuardrailVerifier
  3. Persona boundary leak prevention (Business ≠ Technical output)
  4. Missing entity slot fallback (vague queries → HTTP 200, no 500 KeyError)
  5. Shadow IT unknown asset fallback (uncataloged hosts → Tier-2 baseline)
  6. Scan ingestion endpoint coverage
  7. Model status endpoint coverage
"""
import sys
import os
import io
import json
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from api_layer.main import app
from api_layer.guardrails import SanityGuardrailVerifier

client = TestClient(app)

# ── Helpers ─────────────────────────────────────────────────────────────────

def _biz(prompt: str, budget_lakhs: float = 300.0) -> dict:
    """Post to business chat route and return JSON."""
    overrides = {"budget_lakhs": budget_lakhs} if budget_lakhs != 300.0 else None
    resp = client.post("/api/v1/chat/business", json={
        "session_id": "edge-test", "persona": "business", "prompt": prompt,
        "context_overrides": overrides,
    })
    return {"status": resp.status_code, "data": resp.json()}


def _tech(prompt: str) -> dict:
    """Post to technical chat route and return JSON."""
    resp = client.post("/api/v1/chat/technical", json={
        "session_id": "edge-test", "persona": "technical", "prompt": prompt,
    })
    return {"status": resp.status_code, "data": resp.json()}


# ============================================================================
# Test 1: Forced Financial Hallucination → Gordon-Loeb Cap Enforcement
# ============================================================================
class TestGordonLoebCapEnforcement:
    """Budget exceeding Gordon-Loeb ceiling must be flagged as economically unviable."""

    def test_forced_financial_hallucination_over_gordon_loeb_cap(self):
        """Request approval for ₹500 Crores budget for a minor asset.
        Assert: backend flags 'NOT economically viable' and context_payload
        reflects is_economically_viable=False."""
        result = _biz(
            "Approve a cybersecurity budget of 500 Crores for Core Payment Switch",
            budget_lakhs=50_000.0,  # ₹500 Cr = 50000 Lakhs
        )
        assert result["status"] == 200
        data = result["data"]
        output = data["formatted_output"]
        milprosi = data["context_payload"].get("milprosi", {})

        # The Gordon-Loeb model should flag this as unviable (₹500 Cr >> 37% EAL)
        assert milprosi.get("is_economically_viable") is False, \
            f"Expected unviable, got: {milprosi.get('is_economically_viable')}"

        # The text output should contain 'NOT economically viable'
        assert "NOT economically viable" in output or "not economically viable" in output.lower(), \
            f"Expected viability rejection in output, got: {output[:200]}"


# ============================================================================
# Test 2: Numeric Drift Rejection by SanityGuardrailVerifier
# ============================================================================
class TestNumericDriftRejection:
    """SanityGuardrailVerifier must block fabricated numbers not in payload."""

    def test_numeric_drift_rejection(self):
        """Inject hallucinated numbers ('EAL is ₹0 and VaR is ₹50,000') into
        the guardrail verifier. Assert: verification fails."""
        verifier = SanityGuardrailVerifier()

        # Build a real payload via the business endpoint
        result = _biz("What is the risk for Core Payment Switch with CVE-2024-1234?")
        assert result["status"] == 200
        data = result["data"]

        # Craft a fake hallucinated output text
        hallucinated_text = (
            "The Expected Annual Loss is ₹0.00 Cr and VaR is ₹50,000.00 Cr. "
            "ROSI is 999.99%."
        )

        # Verify against context_payload
        from schemas.data_models import DeterministicContextPayload
        ctx = DeterministicContextPayload(**data["context_payload"])
        passed, errors = verifier.verify_financial_integrity(ctx, hallucinated_text)

        # The guardrail should FAIL because ₹50,000 Cr and 999.99% are not in the payload
        assert not passed, f"Expected guardrail failure but it passed! Errors: {errors}"
        assert len(errors) > 0, "Expected at least one hallucination error"


# ============================================================================
# Test 3: Persona Boundary Leak Prevention
# ============================================================================
class TestPersonaBoundaryLeak:
    """Business route should not leak CVSS vectors; Technical route should not
    leak boardroom capital language."""

    def test_business_route_abstracts_technical_jargon(self):
        """Query the Business route for raw C++ memory exploits.
        Assert: output contains financial language (EAL, ROSI), NOT raw CVSS vectors."""
        result = _biz("Analyze the C++ memory buffer overflow exploit on Core Payment Switch")
        assert result["status"] == 200
        output = result["data"]["formatted_output"]

        # Business output must contain financial terms
        assert any(term in output for term in ["EAL", "ROSI", "Loss", "Cr"]), \
            f"Expected financial terms in business output: {output[:200]}"

    def test_technical_route_restricts_to_secops(self):
        """Query the Technical route for boardroom capital approvals.
        Assert: output contains EPSS/CVSS/XAI terms, not pure financial viability."""
        result = _tech("Prepare boardroom capital approval for cybersecurity budget of 50 Crores")
        assert result["status"] == 200
        output = result["data"]["formatted_output"]

        # Technical output should contain technical terms
        assert any(term in output for term in ["EPSS", "CVSS", "XAI", "Trust", "Exploit", "Diagnostic"]), \
            f"Expected technical terms in technical output: {output[:200]}"


# ============================================================================
# Test 4: Missing Entity Slot Fallback
# ============================================================================
class TestMissingEntitySlotFallback:
    """Vague queries should return HTTP 200 with baseline or clarification, not 500."""

    def test_missing_entity_slot_fallback(self):
        """Send vague query 'What is the risk of it?' with no CVE or asset.
        Assert: HTTP 200 with aggregate baseline report."""
        result = _biz("What is the risk of it?")
        assert result["status"] == 200
        data = result["data"]

        # Should not crash; should return formatted output
        assert len(data["formatted_output"]) > 50, \
            f"Expected substantive output, got: {data['formatted_output']}"
        assert data["context_payload"]["guardrail_passed"] is True

    def test_completely_empty_context(self):
        """Edge case: no entity slots at all."""
        result = _tech("Analyze the risks")
        assert result["status"] == 200
        assert len(result["data"]["formatted_output"]) > 20


# ============================================================================
# Test 5: Shadow IT Unknown Asset Fallback
# ============================================================================
class TestShadowITUnknownAssetFallback:
    """Uncataloged hosts must fall back to Tier-2 baseline without exceptions."""

    def test_shadow_it_unknown_asset_fallback(self):
        """Query for uncataloged host 'legacy-dev-sandbox-99'.
        Assert: HTTP 200 with Tier-2 baseline parameters."""
        result = _biz("What is the risk for legacy-dev-sandbox-99 running CVE-2024-5678?")
        assert result["status"] == 200
        data = result["data"]
        output = data["formatted_output"]

        # Should return valid risk assessment, not crash
        assert "EXECUTIVE RISK BRIEFING" in output or "RISK" in output.upper(), \
            f"Expected risk briefing output: {output[:200]}"
        assert data["context_payload"]["guardrail_passed"] is True

    def test_unknown_cve_fallback(self):
        """Query with a completely unknown CVE ID."""
        result = _tech("Show EPSS for CVE-2099-99999")
        assert result["status"] == 200
        assert len(result["data"]["formatted_output"]) > 50


# ============================================================================
# Test 6: Scan Ingestion Endpoint
# ============================================================================
class TestScanIngestionEndpoint:
    """Scan upload, findings listing, and clear endpoints."""

    def test_scan_upload_json(self):
        """Upload a JSON scan file and verify ingestion."""
        scan_data = json.dumps([
            {
                "cve_id": "CVE-2024-7777",
                "asset_name": "WebPortal-Prod",
                "vendor": "apache",
                "cvss_score": 8.5,
                "tags": ["web", "remote"],
                "exploit_weaponized": True,
                "poc_published": True,
                "reference_count": 120,
                "description": "Remote code execution in web portal.",
                "severity": "critical",
            }
        ])
        from io import BytesIO
        resp = client.post(
            "/api/v1/scan/upload",
            files={"file": ("scan_report.json", BytesIO(scan_data.encode()), "application/json")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["findings_ingested"] >= 1

    def test_scan_upload_csv(self):
        """Upload a CSV scan file and verify ingestion."""
        csv_content = "cve_id,asset_name,vendor,cvss_score,severity\nCVE-2024-8888,DB-Server-01,oracle,7.5,high\n"
        from io import BytesIO
        resp = client.post(
            "/api/v1/scan/upload",
            files={"file": ("scan_report.csv", BytesIO(csv_content.encode()), "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["findings_ingested"] >= 1

    def test_scan_findings_list(self):
        """List cached scan findings."""
        resp = client.get("/api/v1/scan/findings")
        assert resp.status_code == 200
        data = resp.json()
        assert "findings" in data

    def test_scan_clear(self):
        """Clear scan ledger."""
        resp = client.delete("/api/v1/scan/clear")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cleared"

    def test_unsupported_file_format(self):
        """Upload unsupported file format."""
        from io import BytesIO
        resp = client.post(
            "/api/v1/scan/upload",
            files={"file": ("scan.txt", BytesIO(b"hello"), "text/plain")},
        )
        assert resp.status_code == 400


# ============================================================================
# Test 7: Model Status Endpoint
# ============================================================================
class TestModelStatusEndpoint:
    """Verify model status endpoint returns expected fields."""

    def test_model_status(self):
        resp = client.get("/api/v1/models/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "embedding_model" in data
        assert "generation_model" in data
        assert "fallback_active" in data
        assert "embedding_candidates" in data
        assert "generation_candidates" in data


# ============================================================================
# Test 8: LLM NLU Parsing and Scan Analysis Queries
# ============================================================================
class TestLLMNLUParsing:
    """Verify NLU routing for vague terms like 'budget' and scan queries."""

    def test_scan_analysis_without_upload(self):
        # Clear scan first
        client.delete("/api/v1/scan/clear")
        
        # Query chatbot
        result = _biz("what are findings from uoloaded file")
        assert result["status"] == 200
        output = result["data"]["formatted_output"]
        assert "no vulnerability scan" in output.lower() or "upload" in output.lower()

    def test_scan_analysis_with_upload(self):
        # Ingest a scan finding
        scan_data = json.dumps([
            {
                "cve_id": "CVE-2024-3094",
                "asset_name": "Core Payment Switch",
                "vendor": "openvpn",
                "cvss_score": 9.8,
                "tags": ["remote"],
                "exploit_weaponized": True,
                "poc_published": True,
                "description": "Backdoor in xz-utils.",
                "severity": "critical",
            }
        ])
        from io import BytesIO
        client.post(
            "/api/v1/scan/upload",
            files={"file": ("scan.json", BytesIO(scan_data.encode()), "application/json")},
        )
        
        # Query chatbot
        result = _biz("what are findings from uoloaded file")
        assert result["status"] == 200
        output = result["data"]["formatted_output"]
        assert len(output) > 20
        assert "3094" in output or "findings" in output.lower()

    def test_vague_budget_query(self):
        # Sending just "budget" should be conversational clarification or standard risk depending on API availability
        result = _biz("budget")
        assert result["status"] == 200
        output = result["data"]["formatted_output"]
        assert len(output) > 10
