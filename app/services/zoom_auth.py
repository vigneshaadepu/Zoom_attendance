"""
EduTrack — Zoom Server-to-Server OAuth Token Manager
"""
import time
import base64
import logging
import requests
from flask import current_app

logger = logging.getLogger(__name__)

_token_cache = {"token": None, "expires_at": 0}


def get_zoom_token() -> str | None:
    """
    Fetch (and cache) a Zoom Server-to-Server OAuth Bearer token.
    Returns the token string or None on failure.
    """
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    account_id = current_app.config.get("ZOOM_ACCOUNT_ID")
    client_id = current_app.config.get("ZOOM_CLIENT_ID")
    client_secret = current_app.config.get("ZOOM_CLIENT_SECRET")

    if not all([account_id, client_id, client_secret]):
        logger.warning("Zoom credentials not configured.")
        return None

    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    try:
        resp = requests.post(
            "https://zoom.us/oauth/token",
            params={"grant_type": "account_credentials", "account_id": account_id},
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        _token_cache["token"] = data["access_token"]
        _token_cache["expires_at"] = now + data.get("expires_in", 3600)
        logger.info("Zoom OAuth token refreshed.")
        return _token_cache["token"]
    except Exception as exc:
        logger.error(f"Failed to get Zoom token: {exc}")
        return None


def get_meeting_participants(meeting_id: str) -> list[dict]:
    """
    Fetch participant list for a completed meeting via Zoom Reports API.
    """
    token = get_zoom_token()
    if not token:
        return []

    participants = []
    next_page_token = ""

    try:
        while True:
            params = {"page_size": 300}
            if next_page_token:
                params["next_page_token"] = next_page_token

            resp = requests.get(
                f"https://api.zoom.us/v2/report/meetings/{meeting_id}/participants",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            participants.extend(data.get("participants", []))
            next_page_token = data.get("next_page_token", "")
            if not next_page_token:
                break
    except Exception as exc:
        logger.error(f"Failed to get meeting participants for {meeting_id}: {exc}")

    return participants


def get_meeting_info(meeting_id: str) -> dict:
    """Fetch meeting details from Zoom API."""
    token = get_zoom_token()
    if not token:
        return {}

    try:
        resp = requests.get(
            f"https://api.zoom.us/v2/meetings/{meeting_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error(f"Failed to get meeting info for {meeting_id}: {exc}")
        return {}
