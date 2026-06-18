"""
EduTrack — Zoom Webhook Receiver
Handles: meeting.started, meeting.ended, meeting.participant_joined/left
"""
import json
import logging
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app
from app.extensions import db
from app.models import ZoomSession, ParticipantEvent, Professor

logger = logging.getLogger(__name__)
webhook_bp = Blueprint("webhook", __name__)


def _parse_ts(ts_str: str) -> datetime | None:
    """Parse Zoom ISO timestamp to UTC datetime."""
    if not ts_str:
        return None
    try:
        # Zoom sends: "2024-01-15T10:30:00Z"
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        try:
            return datetime.utcfromtimestamp(int(ts_str) / 1000)
        except Exception:
            return datetime.utcnow()


def _find_professor_by_email(email: str) -> Professor | None:
    return Professor.query.filter_by(email=email).first()


def _get_or_create_session(meeting_id: str, host_email: str,
                            topic: str, course_code: str = None) -> ZoomSession | None:
    """Get existing ZoomSession or create a new one."""
    session = ZoomSession.query.filter_by(meeting_id=str(meeting_id)).first()
    if session:
        return session

    professor = _find_professor_by_email(host_email)
    if not professor:
        logger.warning(f"No professor found for host email: {host_email}")
        # Create session without professor (will need to link later)
        return None

    session = ZoomSession(
        meeting_id=str(meeting_id),
        topic=topic,
        host_email=host_email,
        professor_id=professor.id,
        course_code=course_code,
    )
    db.session.add(session)
    db.session.flush()
    return session


@webhook_bp.route("/webhook/zoom", methods=["POST"])
def zoom_webhook():
    """
    Main Zoom webhook receiver.
    Verifies HMAC signature and dispatches to appropriate handler.
    """
    # Verify signature
    from app.services.zoom_webhook import verify_webhook_signature
    if not verify_webhook_signature(request):
        logger.warning("Webhook signature verification failed.")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    event_type = payload.get("event", "")

    # Zoom URL validation challenge
    if event_type == "endpoint.url_validation":
        plain_token = payload.get("payload", {}).get("plainToken", "")
        import hmac, hashlib
        secret = current_app.config.get("ZOOM_WEBHOOK_SECRET_TOKEN", "")
        encrypted = hmac.new(
            secret.encode("utf-8"),
            plain_token.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return jsonify({
            "plainToken": plain_token,
            "encryptedToken": encrypted,
        })

    obj = payload.get("payload", {}).get("object", {})
    meeting_id = str(obj.get("id", ""))
    topic = obj.get("topic", "")
    host_email = obj.get("host_email", "")

    # Respond 200 immediately (Zoom requires fast response)
    # Process in Celery task asynchronously

    logger.info(f"Zoom webhook received: {event_type} for meeting {meeting_id}")

    try:
        if event_type == "meeting.started":
            _handle_meeting_started(obj, meeting_id, topic, host_email)

        elif event_type == "meeting.ended":
            _handle_meeting_ended(obj, meeting_id)

        elif event_type == "meeting.participant_joined":
            _handle_participant_joined(obj, meeting_id)

        elif event_type == "meeting.participant_left":
            _handle_participant_left(obj, meeting_id)

    except Exception as exc:
        logger.error(f"Webhook processing error [{event_type}]: {exc}", exc_info=True)
        db.session.rollback()

    return jsonify({"status": "ok"}), 200


def _handle_meeting_started(obj: dict, meeting_id: str, topic: str, host_email: str):
    try:
        session = ZoomSession.query.filter_by(meeting_id=meeting_id).first()
        if not session:
            professor = _find_professor_by_email(host_email)
            if not professor:
                logger.warning(f"meeting.started: No professor for {host_email}")
                return

            session = ZoomSession(
                meeting_id=meeting_id,
                topic=topic,
                host_email=host_email,
                professor_id=professor.id,
                status="live",
                actual_start=datetime.utcnow(),
            )
            db.session.add(session)
        else:
            session.status = "live"
            session.actual_start = datetime.utcnow()

        db.session.commit()
        logger.info(f"Meeting started: {meeting_id}")
    except Exception as exc:
        db.session.rollback()
        logger.error(f"_handle_meeting_started error: {exc}", exc_info=True)


def _handle_meeting_ended(obj: dict, meeting_id: str):
    try:
        session = ZoomSession.query.filter_by(meeting_id=meeting_id).first()
        if not session:
            logger.warning(f"meeting.ended: Session not found for {meeting_id}")
            return

        end_time = datetime.utcnow()
        session.status = "completed"
        session.actual_end = end_time
        db.session.commit()

        # Dispatch async finalization task
        from app.tasks.finalize_session import finalize_attendance_task
        finalize_attendance_task.delay(session.id)

        logger.info(f"Meeting ended: {meeting_id}. Finalization task queued.")
    except Exception as exc:
        db.session.rollback()
        logger.error(f"_handle_meeting_ended error: {exc}", exc_info=True)


def _handle_participant_joined(obj: dict, meeting_id: str):
    participant = obj.get("participant", {})
    try:
        session = ZoomSession.query.filter_by(meeting_id=meeting_id).first()
        if not session:
            logger.warning(f"participant_joined: Session not found for {meeting_id}")
            return

        event = ParticipantEvent(
            session_id=session.id,
            raw_name=participant.get("user_name", ""),
            raw_email=participant.get("email", ""),
            event_type="joined",
            event_timestamp=_parse_ts(participant.get("join_time")) or datetime.utcnow(),
            zoom_user_id=participant.get("user_id", participant.get("participant_user_uuid", "")),
        )
        db.session.add(event)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.error(f"_handle_participant_joined error: {exc}", exc_info=True)


def _handle_participant_left(obj: dict, meeting_id: str):
    participant = obj.get("participant", {})
    try:
        session = ZoomSession.query.filter_by(meeting_id=meeting_id).first()
        if not session:
            return

        event = ParticipantEvent(
            session_id=session.id,
            raw_name=participant.get("user_name", ""),
            raw_email=participant.get("email", ""),
            event_type="left",
            event_timestamp=_parse_ts(participant.get("leave_time")) or datetime.utcnow(),
            zoom_user_id=participant.get("user_id", participant.get("participant_user_uuid", "")),
        )
        db.session.add(event)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.error(f"_handle_participant_left error: {exc}", exc_info=True)
