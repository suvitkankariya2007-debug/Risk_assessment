"""
tests/test_api_layer.py
=======================
Integration tests for the FastAPI chatbot layer (api_layer/).

Covers:
  - POST /api/v1/chat/business
  - POST /api/v1/chat/technical
  - POST /api/v1/models/stream-update

Uses unittest.mock.patch to avoid live LLM API calls.
"""
import sys
import os
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from api_layer.main import app
from api_layer.synthesizer import call_external_llm
from api_layer.guardrails import SanityGuardrailVerifier


client = TestClient(app)


# ============================================================================
# Helpers
# ============================================================================

def _make_business_llm_response(data: dict) -> str:
    """Generate a valid business briefing string using exact payload numbers."""
    viable_str = (
        "economically viable"
        if data.get("is_economically_viable", True)
        else "NOT economically viable (exceeds Gordon-Loeb ceiling)"
    )
    return (
        f"EXECUTIVE RISK BRIEFING\n"
        f"Target Asset: {data['asset_name']} | Threat CVE: {data['cve_id']}\n\n"
        f"1. Financial Exposure:\n"
        f"   - Expected Annual Loss (EAL): ₹{data['eal_cr']:.2f} Cr\n"
        f"   - 95% Value-at-Risk (VaR): ₹{data['var_95_cr']:.2f} Cr\n"
        f"   - Operational Downtime Loss: ₹{data['primary_loss_cr']:.2f} Cr\n"
        f"   - Regulatory & Secondary Penalties: ₹{data['secondary_loss_cr']:.2f} Cr\n\n"
        f"2. Security Economics & Recommendation:\n"
        f"   - Proposed Control Cost: ₹{data['control_cost_cr']:.2f} Cr\n"
        f"   - Anticipated Risk Reduction: ₹{data['risk_reduced_cr']:.2f} Cr\n"
        f"   - Return on Security Investment (ROSI): {data['rosi_pct']:.1f}%\n"
        f"   - Gordon-Loeb Capital Ceiling: ₹{data['gordon_loeb_cap_cr']:.2f} Cr\n"
        f"   - Assessment: The proposed investment is {viable_str}.\n"
    )


def _make_technical_llm_response(data: dict) -> str:
    """Generate a valid technical diagnostic string using exact payload numbers."""
    tokens_str = ", ".join(data["salient_tokens"]) if data.get("salient_tokens") else "remote, code_execution"
    odds_ratio = data["epss_prob"] / max(1e-6, 1.0 - data["epss_prob"])
    return (
        f"TECHNICAL SECOPS DIAGNOSTIC REPORT\n"
        f"Asset: {data['asset_name']} | CVE ID: {data['cve_id']}\n\n"
        f"1. Threat & Exploit Intelligence:\n"
        f"   - CVSS Vector: {data['cvss_vector']} (Base Score: {data['cvss_score']})\n"
        f"   - EPSS Exploit Probability: {data['epss_prob']:.4f} ({data['epss_prob']*100:.2f}%)\n"
        f"   - EPSS Exploit Odds Ratio: {odds_ratio:.4f}\n"
        f"   - EPSS Model Z-Score: {data['epss_z_score']:.4f}\n\n"
        f"2. Explainable AI (XAI) Alignment:\n"
        f"   - XAI Trust Score: {data['trust_score_pct']:.1f}%\n"
        f"   - Alignment Status: {data['alignment_status']}\n"
        f"   - Salient Feature Tokens: [{tokens_str}]\n\n"
        f"3. Risk & Loss Parameters:\n"
        f"   - EAL: ₹{data['eal_cr']:.4f} Cr | VaR (95%): ₹{data['var_95_cr']:.4f} Cr\n"
        f"   - Primary Downtime Loss: ₹{data['primary_loss_cr']:.4f} Cr\n"
        f"   - Secondary Regulatory Loss: ₹{data['secondary_loss_cr']:.4f} Cr\n"
        f"   - ROSI: {data['rosi_pct']:.2f}% | Viable: {data['is_economically_viable']}\n"
    )


def _mock_llm_side_effect(prompt: str, data: dict) -> str:
    """Side-effect factory: returns template-style text with exact payload numbers."""
    persona_hint = prompt.lower()
    if "audience: secops" in persona_hint or "audience: technical" in persona_hint:
        return _make_technical_llm_response(data)
    return _make_business_llm_response(data)


# ============================================================================
# Class 1: TestBusinessChatbotEndpoint
# ============================================================================

class TestBusinessChatbotEndpoint:
    """Tests for POST /api/v1/chat/business."""

    def test_business_chat_success(self):
        """
        Valid business request with correctly grounded LLM mock.
        Expects HTTP 200, guardrail True, persona 'business',
        financial metrics present, no raw CVSS/EPSS odds.
        """
        with patch("api_layer.synthesizer.call_external_llm") as mock_llm:
            mock_llm.side_effect = _mock_llm_side_effect

            response = client.post(
                "/api/v1/chat/business",
                json={
                    "session_id": "test-biz-001",
                    "persona": "business",
                    "prompt": (
                        "Assess risk for Core Payment Switch "
                        "with CVE-2024-3094 and budget 10 Lakhs"
                    ),
                    "context_overrides": None,
                },
            )

            assert response.status_code == 200, f"Response: {response.text}"
            data = response.json()

            # Guardrail must pass because LLM returns exact payload numbers
            assert data["context_payload"]["guardrail_passed"] is True
            assert len(data["context_payload"]["guardrail_errors"]) == 0

            # Persona enum serializes to its value string
            assert data["persona"] == "business"

            # Formatted output must contain the business briefing header
            output = data["formatted_output"]
            assert "EXECUTIVE RISK BRIEFING" in output

            # Financial metrics must be present
            assert "Expected Annual Loss (EAL)" in output
            assert "95% Value-at-Risk (VaR)" in output
            assert "Return on Security Investment (ROSI)" in output

            # Raw CVSS vectors must NOT appear in business output
            assert "CVSS:3.1" not in output
            assert "EPSS Exploit Odds" not in output

    def test_business_chat_hallucination_blocked_by_guardrail(self):
        """
        LLM returns hallucinated financial numbers.
        Expects guardrail_passed=False with detected errors.
        The API still returns 200 but flags the hallucination.
        """
        with patch("api_layer.synthesizer.call_external_llm") as mock_llm:
            mock_llm.return_value = (
                "EXECUTIVE RISK BRIEFING\n"
                "Expected loss is ₹999.99 Crores\n"
                "ROSI: 500.0%\n"
            )

            response = client.post(
                "/api/v1/chat/business",
                json={
                    "session_id": "test-biz-002",
                    "persona": "business",
                    "prompt": "Assess risk for Core Payment Switch",
                    "context_overrides": None,
                },
            )

            # API returns 200 but with guardrail failure
            assert response.status_code == 200
            data = response.json()
            assert data["context_payload"]["guardrail_passed"] is False
            assert len(data["context_payload"]["guardrail_errors"]) > 0

            # Verify the guardrail caught the hallucinated currency figure
            error_text = " ".join(data["context_payload"]["guardrail_errors"]).lower()
            assert "hallucinated" in error_text or "₹999.99" in error_text or "999.99" in error_text


# ============================================================================
# Class 2: TestTechnicalChatbotEndpoint
# ============================================================================

class TestTechnicalChatbotEndpoint:
    """Tests for POST /api/v1/chat/technical."""

    def test_technical_chat_success(self):
        """
        Valid technical request with correctly grounded LLM mock.
        Expects HTTP 200, guardrail True, persona 'technical',
        and technical datapoints present.
        """
        with patch("api_layer.synthesizer.call_external_llm") as mock_llm:
            mock_llm.side_effect = _mock_llm_side_effect

            response = client.post(
                "/api/v1/chat/technical",
                json={
                    "session_id": "test-tech-001",
                    "persona": "technical",
                    "prompt": (
                        "Remediate CVE-2024-3094 on Core Payment Switch "
                        "within 7 days with budget 50 Lakhs"
                    ),
                    "context_overrides": None,
                },
            )

            assert response.status_code == 200, f"Response: {response.text}"
            data = response.json()

            # Guardrail must pass
            assert data["context_payload"]["guardrail_passed"] is True
            assert len(data["context_payload"]["guardrail_errors"]) == 0

            # Persona enum serializes to its value string
            assert data["persona"] == "technical"

            # Formatted output must contain the technical diagnostic header
            output = data["formatted_output"]
            assert "TECHNICAL SECOPS DIAGNOSTIC REPORT" in output

            # The context_payload must contain the required technical datapoints
            ctx = data["context_payload"]
            assert ctx["epss"] is not None, "context_payload must include EPSS data"
            assert ctx["xai"] is not None, "context_payload must include XAI data"
            assert ctx["fair"] is not None, "context_payload must include FAIR data"

            # cve_id
            assert ctx["epss"]["cve_id"] == "CVE-2024-3094"

            # epss_prob must be a valid probability in [0.0, 1.0]
            assert 0.0 <= ctx["epss"]["p_exploit"] <= 1.0

            # xai_trust_score must be a valid percentage in [0.0, 100.0]
            assert 0.0 <= ctx["xai"]["trust_score_pct"] <= 100.0


# ============================================================================
# Class 3: TestStreamingRetrainingBus
# ============================================================================

class TestStreamingRetrainingBus:
    """Tests for POST /api/v1/models/stream-update."""

    def test_telemetry_stream_ingestion_success(self):
        """
        Valid list of telemetry dictionaries should be accepted.
        Expects HTTP 200 with status 'success' and correct sample count.
        """
        telemetry = [
            {
                "vend_microsoft": True,
                "exp_weaponized": True,
                "ref_count": 42,
                "label": 1,
            },
            {
                "vend_apple": True,
                "tag_local": True,
                "ref_count": 5,
                "label": 0,
            },
        ]

        response = client.post(
            "/api/v1/models/stream-update",
            json={"telemetry_batch": telemetry},
        )

        assert response.status_code == 200, f"Response: {response.text}"
        data = response.json()
        assert data["status"] == "success"
        assert data["samples_ingested"] == 2
        assert "model_fitted" in data

    def test_telemetry_stream_invalid_payload(self):
        """
        Malformed payload (string instead of list/dict) should be rejected.
        Expects HTTP 422 Unprocessable Entity.
        """
        response = client.post(
            "/api/v1/models/stream-update",
            json="this is not a valid list or dict payload",
        )

        assert response.status_code == 422
