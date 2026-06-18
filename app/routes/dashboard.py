"""
EduTrack — Dashboard Route
"""
from flask import Blueprint, render_template, jsonify, session
from flask_login import login_required, current_user
from app.models import RegisteredStudent, ZoomSession, AttendanceRecord, AttendanceReport

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    professor_id = current_user.id
    active_course_id = session.get("active_course_id")

    # KPI cards
    total_students = RegisteredStudent.query.filter_by(
        professor_id=professor_id, is_active=True, course_id=active_course_id
    ).count()

    from datetime import datetime, timedelta
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
    sessions_this_month = ZoomSession.query.filter(
        ZoomSession.professor_id == professor_id,
        ZoomSession.actual_start >= month_start,
        ZoomSession.course_id == active_course_id
    ).count()

    # Average attendance rate
    completed_sessions = ZoomSession.query.filter_by(
        professor_id=professor_id, status="completed", course_id=active_course_id
    ).all()

    avg_attendance = 0.0
    if completed_sessions:
        rates = []
        for s in completed_sessions:
            records = AttendanceRecord.query.filter_by(session_id=s.id).all()
            if records:
                present = sum(1 for r in records if r.is_present)
                rates.append(present / len(records) * 100)
        avg_attendance = round(sum(rates) / len(rates), 1) if rates else 0.0

    # At-risk students
    high_risk_count = RegisteredStudent.query.filter_by(
        professor_id=professor_id, is_active=True, risk_label="high", course_id=active_course_id
    ).count()

    # Recent sessions (last 10)
    recent_sessions = ZoomSession.query.filter_by(
        professor_id=professor_id, course_id=active_course_id
    ).order_by(ZoomSession.actual_start.desc()).limit(10).all()

    # Recent reports
    recent_reports = AttendanceReport.query.join(ZoomSession).filter(
        ZoomSession.professor_id == professor_id,
        ZoomSession.course_id == active_course_id
    ).order_by(AttendanceReport.generated_at.desc()).limit(5).all()

    # At-risk students list
    at_risk_students = RegisteredStudent.query.filter(
        RegisteredStudent.professor_id == professor_id,
        RegisteredStudent.is_active == True,
        RegisteredStudent.risk_label.in_(["high", "medium"]),
        RegisteredStudent.course_id == active_course_id
    ).order_by(RegisteredStudent.risk_score.desc()).limit(10).all()

    # Unmatched participants needing review
    unmatched_records = AttendanceRecord.query.join(ZoomSession).filter(
        ZoomSession.professor_id == professor_id,
        ZoomSession.course_id == active_course_id,
        AttendanceRecord.needs_review == True,
    ).order_by(AttendanceRecord.created_at.desc()).limit(10).all()

    # Live session check
    live_session = ZoomSession.query.filter_by(
        professor_id=professor_id, status="live", course_id=active_course_id
    ).first()

    # Chart data: attendance rate per session
    chart_sessions = ZoomSession.query.filter_by(
        professor_id=professor_id, status="completed", course_id=active_course_id
    ).order_by(ZoomSession.actual_start).limit(20).all()

    chart_labels = []
    chart_rates = []
    for s in chart_sessions:
        records = AttendanceRecord.query.filter_by(session_id=s.id).all()
        if records:
            present = sum(1 for r in records if r.is_present)
            rate = round(present / len(records) * 100, 1)
            chart_labels.append(
                s.actual_start.strftime("%b %d") if s.actual_start else f"Session {s.id}"
            )
            chart_rates.append(rate)

    return render_template(
        "dashboard.html",
        total_students=total_students,
        sessions_this_month=sessions_this_month,
        avg_attendance=avg_attendance,
        high_risk_count=high_risk_count,
        recent_sessions=recent_sessions,
        recent_reports=recent_reports,
        at_risk_students=at_risk_students,
        unmatched_records=unmatched_records,
        live_session=live_session,
        chart_labels=chart_labels,
        chart_rates=chart_rates,
    )
