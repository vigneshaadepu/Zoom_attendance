"""
EduTrack — JSON API Endpoints
"""
from flask import Blueprint, jsonify, request, session
from flask_login import login_required, current_user
from app.models import ZoomSession, AttendanceRecord, RegisteredStudent, ParticipantEvent

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/attendance/trend")
@login_required
def attendance_trend():
    """
    GET /api/attendance/trend?days=30
    Returns per-session attendance rates for Chart.js.
    """
    days = int(request.args.get("days", 30))
    active_course_id = session.get("active_course_id")

    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)

    query = ZoomSession.query.filter(
        ZoomSession.professor_id == current_user.id,
        ZoomSession.status == "completed",
        ZoomSession.actual_start >= cutoff,
        ZoomSession.course_id == active_course_id
    )

    sessions = query.order_by(ZoomSession.actual_start).all()

    labels, rates, session_ids = [], [], []
    for s in sessions:
        records = AttendanceRecord.query.filter_by(session_id=s.id).all()
        if records:
            present = sum(1 for r in records if r.is_present)
            rate = round(present / len(records) * 100, 1)
            labels.append(s.actual_start.strftime("%b %d") if s.actual_start else f"#{s.id}")
            rates.append(rate)
            session_ids.append(s.id)

    return jsonify({"labels": labels, "rates": rates, "session_ids": session_ids})


@api_bp.route("/students/risk")
@login_required
def students_risk():
    """
    GET /api/students/risk
    Returns at-risk students with scores.
    """
    active_course_id = session.get("active_course_id")
    students = RegisteredStudent.query.filter(
        RegisteredStudent.professor_id == current_user.id,
        RegisteredStudent.is_active == True,
        RegisteredStudent.risk_label.in_(["high", "medium"]),
        RegisteredStudent.course_id == active_course_id
    ).order_by(RegisteredStudent.risk_score.desc()).limit(20).all()

    return jsonify([{
        "id": s.id,
        "name": s.full_name,
        "student_id": s.student_id,
        "course_code": s.course_code,
        "risk_score": round(s.risk_score or 0, 3),
        "risk_label": s.risk_label or "low",
        "attendance_rate": s.attendance_rate,
    } for s in students])


@api_bp.route("/session/<int:session_id>/live")
@login_required
def session_live(session_id):
    """
    GET /api/session/<id>/live
    Returns current live participant count (polls every 30s).
    """
    session_obj = ZoomSession.query.filter_by(
        id=session_id, professor_id=current_user.id
    ).first_or_404()

    if session_obj.status != "live":
        return jsonify({
            "is_live": False,
            "participant_count": 0,
            "duration_seconds": 0,
        })

    # Count unique users who joined but haven't left
    joined_users = set(
        e.zoom_user_id for e in
        ParticipantEvent.query.filter_by(session_id=session_id, event_type="joined").all()
    )
    left_users = set(
        e.zoom_user_id for e in
        ParticipantEvent.query.filter_by(session_id=session_id, event_type="left").all()
    )
    active_count = len(joined_users - left_users)

    from datetime import datetime
    duration = 0
    if session_obj.actual_start:
        duration = int((datetime.utcnow() - session_obj.actual_start).total_seconds())

    return jsonify({
        "is_live": True,
        "participant_count": active_count,
        "duration_seconds": duration,
        "topic": session_obj.topic,
    })


@api_bp.route("/students/<int:student_id>/attendance_history")
@login_required
def student_attendance_history(student_id):
    """GET chart data for individual student attendance over time."""
    student = RegisteredStudent.query.filter_by(
        id=student_id, professor_id=current_user.id
    ).first_or_404()

    records = AttendanceRecord.query.filter_by(
        student_id=student_id
    ).order_by(AttendanceRecord.created_at).all()

    labels = []
    statuses = []
    durations = []

    for r in records:
        s = r.session
        date = (s.actual_start or s.scheduled_start)
        labels.append(date.strftime("%b %d") if date else f"Session {s.id}")
        statuses.append(1 if r.is_present else 0)
        durations.append(round(r.total_duration_seconds / 60, 1) if r.total_duration_seconds else 0)

    return jsonify({
        "labels": labels,
        "statuses": statuses,
        "durations": durations,
        "attendance_rate": student.attendance_rate,
    })


@api_bp.route("/dashboard/stats")
@login_required
def dashboard_stats():
    """Refresh dashboard KPIs via AJAX."""
    professor_id = current_user.id
    active_course_id = session.get("active_course_id")

    total_students = RegisteredStudent.query.filter_by(
        professor_id=professor_id, is_active=True, course_id=active_course_id
    ).count()

    live_session = ZoomSession.query.filter_by(
        professor_id=professor_id, status="live", course_id=active_course_id
    ).first()

    high_risk = RegisteredStudent.query.filter_by(
        professor_id=professor_id, is_active=True, risk_label="high", course_id=active_course_id
    ).count()

    return jsonify({
        "total_students": total_students,
        "high_risk_count": high_risk,
        "has_live_session": live_session is not None,
        "live_session_id": live_session.id if live_session else None,
    })


@api_bp.route("/courses")
@login_required
def list_courses():
    """Get unique courses for the current professor."""
    from app.models import Course
    courses = Course.query.filter_by(professor_id=current_user.id).all()
    return jsonify([{"id": c.id, "code": c.code, "name": c.name} for c in courses])
