"""
EduTrack — Zoom Webhook Signature Verification
"""
import hmac
import hashlib
import logging
from flask import Request, current_app

logger = logging.getLogger(__name__)


def verify_webhook_signature(request: Request) -> bool:
    """
    Verify Zoom webhook HMAC-SHA256 signature.
    Zoom signs: "v0:{timestamp}:{body}" with the webhook secret.
    """
    secret_token = current_app.config.get("ZOOM_WEBHOOK_SECRET_TOKEN", "")
    if not secret_token:
        logger.warning("ZOOM_WEBHOOK_SECRET_TOKEN not set — skipping verification.")
        return True  # Allow in unconfigured dev environments

    signature = request.headers.get("x-zm-signature", "")
    timestamp = request.headers.get("x-zm-request-timestamp", "")
    body = request.get_data(as_text=True)

    if not signature or not timestamp:
        logger.warning("Missing Zoom signature headers.")
        return False

    # Prevent replay attacks (reject if timestamp > 5 minutes old)
    import time
    try:
        if abs(time.time() - int(timestamp)) > 300:
            logger.warning("Zoom webhook timestamp too old (replay attack?).")
            return False
    except (ValueError, TypeError):
        return False

    message = f"v0:{timestamp}:{body}"
    expected = "v0=" + hmac.new(
        secret_token.encode("utf-8"),
        msg=message.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        logger.warning("Zoom webhook signature mismatch.")
        return False

    return True


def parse_webhook_payload(payload: dict) -> tuple[str, dict]:
    """
    Extract event type and relevant payload from Zoom webhook body.
    Returns (event_type, data_dict)
    """
    event_type = payload.get("event", "")
    payload_data = payload.get("payload", {}).get("object", {})
    return event_type, payload_data
