from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def test_asset_explain_endpoint_returns_details():
    client = TestClient(app)

    response = client.get('/api/v1/quant/assets/1/explain', params={'persona': 'ciso'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['asset_id'] == 1
    assert payload['business_unit'] == 'Core Banking'
    assert payload['persona'] == 'ciso'
    assert 'explanation' in payload
    assert 'fair_cam' in payload
    assert 'primary_loss_breakdown' in payload
    assert 'secondary_loss_breakdown' in payload
    assert 'threat_community' in payload
    assert 'vendor_dependency' in payload
    assert len(payload['explanation']) > 0


def test_live_telemetry_and_drill_cycle():
    client = TestClient(app)

    feed_response = client.get('/api/v1/telemetry/live-feed')
    assert feed_response.status_code == 200, feed_response.text
    events = feed_response.json()
    assert len(events) <= 10
    assert events[0]['source']
    assert events[0]['status'] in {'BLOCKED', 'ANOMALY_DETECTED', 'SCANNED'}

    trigger_response = client.post('/api/v1/telemetry/trigger-drill', json={'attack_type': 'ddos'})
    assert trigger_response.status_code == 200, trigger_response.text
    trigger_payload = trigger_response.json()
    assert trigger_payload['attack_active'] is True
    assert trigger_payload['target_asset'] == 'pay-gw-03'
    assert trigger_payload['attack_type'] == 'ddos'
    assert trigger_payload['eal_cr'] >= 0

    reset_response = client.post('/api/v1/telemetry/reset-drill', json={})
    assert reset_response.status_code == 200, reset_response.text
    reset_payload = reset_response.json()
    assert reset_payload['attack_active'] is False
    assert reset_payload['target_asset'] is None
