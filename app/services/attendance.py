"""
EduTrack — Attendance Duration Accumulation & Finalization Service
"""
import logging
from datetime import datetime, timezone
from collections import defaultdict

from app.extensions import db
from app.models import (
    ZoomSession, RegisteredStudent, ParticipantEvent,
    AttendanceRecord
)

logger = logging.getLogger(__name__)


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def accumulate_duration(events: list) -> dict:
    """
    Given a list of ParticipantEvent objects for a session,
    accumulate total duration (seconds) per zoom_user_id.

    Handles multiple join/leave cycles (re-joins).

    Returns:
        dict: {zoom_user_id: {"total_seconds": int, "raw_name": str,
                              "raw_email": str, "join_times": [...],
                              "leave_times": [...]}}
    """
    # Group events by user
    user_events = defaultdict(list)
    for event in events:
        user_events[event.zoom_user_id].append(event)

    durations = {}
    for user_id, user_evts in user_events.items():
        # Sort events chronologically
        sorted_events = sorted(user_evts, key=lambda e: e.event_timestamp)

        raw_name = sorted_events[0].raw_name
        raw_email = sorted_events[0].raw_email or ""
        total_seconds = 0
        join_stack = []
        join_times = []
        leave_times = []

        for evt in sorted_events:
            if evt.event_type == "joined":
                join_stack.append(evt.event_timestamp)
                join_times.append(evt.event_timestamp)
            elif evt.event_type == "left" and join_stack:
                join_time = join_stack.pop()
                delta = (evt.event_timestamp - join_time).total_seconds()
                if delta > 0:
                    total_seconds += int(delta)
                leave_times.append(evt.event_timestamp)

        durations[user_id] = {
            "total_seconds": total_seconds,
            "raw_name": raw_name,
            "raw_email": raw_email,
            "join_times": join_times,
            "leave_times": leave_times,
            "pending_joins": list(join_stack),  # still in meeting when ended
        }

    return durations


def finalize_session_attendance(session_id: int, meeting_end_time: datetime = None) -> bool:
    """
    Full post-session processing pipeline:
    1. Fetch all ParticipantEvents for session
    2. Accumulate durations (handle re-joins)
    3. Handle still-in-meeting participants (use meeting end time)
    4. Run 3-layer ML matching against RegisteredStudent
    5. Create/update AttendanceRecord for every registered student
    6. Return True on success
    """
    from app.services.matching import match_participant
    from flask import current_app

    try:
        session = ZoomSession.query.get(session_id)
        if not session:
            logger.error(f"Session {session_id} not found.")
            return False

        threshold = current_app.config.get("SESSION_DURATION_THRESHOLD", 3600)
        end_time = meeting_end_time or session.actual_end or utcnow()

        # Step 1: Fetch all events
        events = ParticipantEvent.query.filter_by(session_id=session_id).all()
        if not events:
            logger.warning(f"No participant events found for session {session_id}.")

        # Step 2 & 3: Accumulate durations
        durations = accumulate_duration(events)

        # Add time for participants still in meeting when it ended
        for user_id, data in durations.items():
            for pending_join in data.get("pending_joins", []):
                extra = (end_time - pending_join).total_seconds()
                if extra > 0:
                    data["total_seconds"] += int(extra)

        # Step 4: Get registered students for this professor/course
        students = RegisteredStudent.query.filter_by(
            professor_id=session.professor_id,
            is_active=True,
        ).all()

        if session.course_code:
            course_students = [s for s in students if s.course_code == session.course_code]
            if course_students:
                students = course_students

        # Step 5: Match each zoom participant to a student
        matched_student_ids = set()
        zoom_participant_records = []  # (student, duration_data, confidence, method)

        for user_id, data in durations.items():
            result = match_participant(
                zoom_name=data["raw_name"],
                zoom_email=data["raw_email"],
                students=students,
            )
            if result:
                student, confidence, method = result
                zoom_participant_records.append(
                    (student, data, confidence, method)
                )
                matched_student_ids.add(student.id)
            else:
                # Unmatched — create a placeholder record with no student link
                zoom_participant_records.append((None, data, 0.0, "unmatched"))

        # Step 6: Create/update AttendanceRecord for every registered student
        for student in students:
            # Find if this student was matched
            record_data = next(
                (r for r in zoom_participant_records if r[0] and r[0].id == student.id),
                None,
            )

            existing = AttendanceRecord.query.filter_by(
                student_id=student.id, session_id=session_id
            ).first()

            if record_data:
                _, data, confidence, method = record_data
                total_secs = data["total_seconds"]
                is_present = total_secs >= threshold
                join_t = data["join_times"][0] if data["join_times"] else None
                leave_t = data["leave_times"][-1] if data["leave_times"] else None

                if existing:
                    existing.total_duration_seconds = total_secs
                    existing.is_present = is_present
                    existing.match_confidence_score = confidence
                    existing.match_method = method
                    existing.join_time = join_t
                    existing.leave_time = leave_t
                    existing.zoom_display_name = data["raw_name"]
                    existing.zoom_email = data["raw_email"]
                    existing.needs_review = confidence < 0.9
                else:
                    ar = AttendanceRecord(
                        student_id=student.id,
                        session_id=session_id,
                        zoom_display_name=data["raw_name"],
                        zoom_email=data["raw_email"],
                        join_time=join_t,
                        leave_time=leave_t,
                        total_duration_seconds=total_secs,
                        is_present=is_present,
                        match_confidence_score=confidence,
                        match_method=method,
                        needs_review=confidence < 0.9,
                    )
                    db.session.add(ar)
            else:
                # Absent — not found in Zoom at all
                if existing:
                    existing.is_present = False
                    existing.match_method = "absent"
                    existing.total_duration_seconds = 0
                else:
                    ar = AttendanceRecord(
                        student_id=student.id,
                        session_id=session_id,
                        is_present=False,
                        match_method="absent",
                        total_duration_seconds=0,
                        match_confidence_score=0.0,
                    )
                    db.session.add(ar)

        # Update session status
        session.status = "completed"
        session.actual_end = end_time

        db.session.commit()
        logger.info(f"Finalized attendance for session {session_id}. "
                    f"{len(students)} students processed.")
        return True

    except Exception as exc:
        logger.error(f"Error finalizing session {session_id}: {exc}", exc_info=True)
        db.session.rollback()
        return False
