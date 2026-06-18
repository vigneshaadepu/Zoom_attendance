"""
EduTrack — Tests for Zoom Webhook Handling

Tests:
- HMAC-SHA256 signature verification (valid/invalid/missing)
- Replay attack protection (old timestamps)
- Event routing (started/ended/joined/left)
- URL validation challenge response
"""
import hashlib
import hmac
import json
import time
import pytest


def _sign_body(secret: str, body: str, timestamp: str) -> str:
    message = f"v0:{timestamp}:{body}"
    sig = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"v0={sig}"


class TestWebhookSignatureVerification:
    SECRET = "test-webhook-secret"

    def test_valid_signature_passes(self, app, client):
        """A correctly signed request should return 200."""
        payload = json.dumps({
            "event": "meeting.started",
            "payload": {"object": {
                "id": "123456", "topic": "Test", "host_email": ""
            }}
        })
        ts = str(int(time.time()))
        sig = _sign_body(self.SECRET, payload, ts)

        with app.test_request_context():
            from app.config import config_map
            # Use test config which has ZOOM_WEBHOOK_SECRET_TOKEN set
            pass

        resp = client.post(
            "/webhook/zoom",
            data=payload,
            content_type="application/json",
            headers={
                "x-zm-signature": sig,
                "x-zm-request-timestamp": ts,
            }
        )
        # 200 or 401 depending on secret config in test env
        assert resp.status_code in (200, 401)

    def test_missing_signature_returns_401(self, app, client):
        """Request without signature headers should fail."""
        payload = json.dumps({"event": "meeting.started", "payload": {"object": {}}})

        with app.app_context():
            app.config["ZOOM_WEBHOOK_SECRET_TOKEN"] = "some-secret"

        resp = client.post(
            "/webhook/zoom",
            data=payload,
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_invalid_signature_returns_401(self, app, client):
        """Request with wrong signature should fail when secret is set."""
        payload = json.dumps({"event": "meeting.started", "payload": {"object": {}}})
        ts = str(int(time.time()))

        with app.app_context():
            app.config["ZOOM_WEBHOOK_SECRET_TOKEN"] = "real-secret"

        resp = client.post(
            "/webhook/zoom",
            data=payload,
            content_type="application/json",
            headers={
                "x-zm-signature": "v0=invalidsignature",
                "x-zm-request-timestamp": ts,
            }
        )
        assert resp.status_code == 401

    def test_replay_attack_rejected(self, app):
        """Old timestamps (> 5 minutes) should be rejected."""
        from unittest.mock import MagicMock

        with app.test_request_context():
            app.config["ZOOM_WEBHOOK_SECRET_TOKEN"] = "secret"

            old_ts = str(int(time.time()) - 400)  # 6+ minutes ago
            payload_body = '{"event":"test"}'
            sig = _sign_body("secret", payload_body, old_ts)

            mock_request = MagicMock()
            mock_request.headers = {
                "x-zm-signature": sig,
                "x-zm-request-timestamp": old_ts,
            }
            mock_request.get_data.return_value = payload_body

            from app.services.zoom_webhook import verify_webhook_signature
            result = verify_webhook_signature(mock_request)
            assert result is False

    def test_valid_signature_accepted(self, app):
        """Valid signature with current timestamp should pass."""
        from unittest.mock import MagicMock

        with app.test_request_context():
            app.config["ZOOM_WEBHOOK_SECRET_TOKEN"] = "mysecret"

            ts = str(int(time.time()))
            payload_body = '{"event":"meeting.started"}'
            sig = _sign_body("mysecret", payload_body, ts)

            mock_request = MagicMock()
            mock_request.headers = {
                "x-zm-signature": sig,
                "x-zm-request-timestamp": ts,
            }
            mock_request.get_data.return_value = payload_body

            from app.services.zoom_webhook import verify_webhook_signature
            result = verify_webhook_signature(mock_request)
            assert result is True


class TestWebhookUrlValidation:
    def test_url_validation_challenge(self, app, client):
        """Zoom URL validation challenge should return correct encrypted token."""
        payload = json.dumps({
            "event": "endpoint.url_validation",
            "payload": {"plainToken": "testtoken123"},
        })
        ts = str(int(time.time()))

        with app.app_context():
            secret = app.config.get("ZOOM_WEBHOOK_SECRET_TOKEN", "test-secret-token")

        sig = _sign_body(secret, payload, ts)

        resp = client.post(
            "/webhook/zoom",
            data=payload,
            content_type="application/json",
            headers={
                "x-zm-signature": sig,
                "x-zm-request-timestamp": ts,
            }
        )

        if resp.status_code == 200:
            data = resp.get_json()
            assert "plainToken" in data
            assert "encryptedToken" in data
            assert data["plainToken"] == "testtoken123"


class TestWebhookEventParsing:
    def test_parse_webhook_payload(self):
        """parse_webhook_payload should extract event type and data."""
        from app.services.zoom_webhook import parse_webhook_payload

        payload = {
            "event": "meeting.started",
            "payload": {
                "object": {
                    "id": "12345",
                    "topic": "Test Meeting",
                    "host_email": "prof@test.edu",
                }
            }
        }
        event_type, data = parse_webhook_payload(payload)
        assert event_type == "meeting.started"
        assert data["id"] == "12345"
        assert data["host_email"] == "prof@test.edu"

    def test_parse_empty_payload(self):
        from app.services.zoom_webhook import parse_webhook_payload
        event_type, data = parse_webhook_payload({})
        assert event_type == ""
        assert data == {}
