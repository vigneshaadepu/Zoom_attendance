"""
EduTrack — Session Management Routes
"""
import logging
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, session as flask_session
from flask_login import login_required, current_user
from app.extensions import db
from app.models import ZoomSession, AttendanceRecord, ParticipantEvent

logger = logging.getLogger(__name__)
sessions_bp = Blueprint("sessions", __name__, url_prefix="/sessions")


@sessions_bp.route("/")
@login_required
def list_sessions():
    active_course_id = flask_session.get("active_course_id")
    sessions = ZoomSession.query.filter_by(
        professor_id=current_user.id, course_id=active_course_id
    ).order_by(ZoomSession.actual_start.desc()).all()

    # Attach attendance stats
    session_data = []
    for s in sessions:
        records = AttendanceRecord.query.filter_by(session_id=s.id).all()
        total = len(records)
        present = sum(1 for r in records if r.is_present)
        rate = round(present / total * 100, 1) if total > 0 else 0.0

        session_data.append({
            "session": s,
            "total_students": total,
            "present": present,
            "attendance_rate": rate,
        })

    return render_template("sessions/list.html", session_data=session_data)


@sessions_bp.route("/<int:session_id>")
@login_required
def session_detail(session_id):
    session = ZoomSession.query.filter_by(
        id=session_id, professor_id=current_user.id
    ).first_or_404()

    records = AttendanceRecord.query.filter_by(
        session_id=session_id
    ).order_by(AttendanceRecord.is_present.desc()).all()

    # Sort: absent, partial, present
    absent = [r for r in records if not r.is_present and not r.total_duration_seconds]
    partial = [r for r in records if not r.is_present and r.total_duration_seconds]
    present = [r for r in records if r.is_present]
    sorted_records = absent + partial + present

    # Raw events for timeline
    events = ParticipantEvent.query.filter_by(
        session_id=session_id
    ).order_by(ParticipantEvent.event_timestamp).limit(200).all()

    return render_template(
        "sessions/detail.html",
        session=session,
        records=sorted_records,
        events=events,
        present_count=len(present),
        partial_count=len(partial),
        absent_count=len(absent),
    )


@sessions_bp.route("/sync", methods=["POST"])
@login_required
def sync_sessions():
    """Manually trigger Zoom session sync."""
    try:
        from app.services.zoom_auth import get_zoom_token
        token = get_zoom_token()
        if not token:
            flash("Zoom credentials not configured. Please check your .env file.", "warning")
            return redirect(url_for("sessions.list_sessions"))

        flash("Zoom sync triggered. Sessions will appear shortly.", "success")
    except Exception as exc:
        logger.error(f"Session sync failed: {exc}")
        flash("Zoom sync failed. Check your credentials.", "danger")

    return redirect(url_for("sessions.list_sessions"))


@sessions_bp.route("/upload-csv", methods=["GET", "POST"])
@login_required
def upload_csv():
    """Upload a Zoom CSV Participant list and compute attendance instantly."""
    from app.models import RegisteredStudent
    # Get unique course codes for select dropdown
    all_courses = db.session.query(RegisteredStudent.course_code).filter_by(
        professor_id=current_user.id, is_active=True
    ).distinct().all()
    courses = [c[0] for c in all_courses]

    if request.method == "POST":
        import csv
        import io
        from datetime import datetime, timedelta
        
        if "file" not in request.files:
            flash("No file provided.", "danger")
            return redirect(request.url)

        file = request.files["file"]
        if not file.filename.endswith(".csv"):
            flash("Please upload a valid CSV file.", "danger")
            return redirect(request.url)

        course_code = "ALL"

        # Read CSV data
        try:
            stream = io.StringIO(file.read().decode("utf-8"), newline="")
            csv_reader = csv.reader(stream)
            rows = list(csv_reader)
        except Exception as exc:
            flash(f"Failed to read CSV: {exc}", "danger")
            return redirect(request.url)

        if not rows:
            flash("CSV file is empty.", "danger")
            return redirect(request.url)

        # Zoom CSV participant reports usually have headers like:
        # Name (Original Name), User Email, Join Time, Leave Time, Duration (Minutes)
        # Scan for Meeting ID, Topic, or Start Time metadata at the top rows
        meeting_id = None
        topic_from_csv = None
        start_time_from_csv = None

        for i, row in enumerate(rows):
            row_lower = [str(cell).strip().lower() for cell in row if cell]
            for j, cell in enumerate(row_lower):
                if "meeting id" in cell or "meeting number" in cell:
                    for next_val in row[j+1:]:
                        val_clean = str(next_val).strip().replace("-", "").replace(" ", "")
                        if val_clean.isdigit() and len(val_clean) >= 9:
                            meeting_id = val_clean
                            break
                elif "topic" in cell or "meeting topic" in cell:
                    for next_val in row[j+1:]:
                        if next_val and str(next_val).strip():
                            topic_from_csv = str(next_val).strip()
                            break
                elif "start time" in cell or "actual start" in cell:
                    for next_val in row[j+1:]:
                        if next_val and str(next_val).strip():
                            start_time_from_csv = str(next_val).strip()
                            break

        # Search for participant list header row
        header_idx = -1
        for i, row in enumerate(rows):
            row_joined = " ".join(row).lower()
            if "name" in row_joined and ("join time" in row_joined or "user email" in row_joined or "email" in row_joined):
                header_idx = i
                break

        if header_idx == -1:
            header_idx = 0

        headers = [h.strip() for h in rows[header_idx]]
        data_rows = rows[header_idx + 1:]

        # Clean/extract required columns from headers:
        # [Participant Name, Email Address, Join Time, Leave Time, Duration, Meeting ID]
        name_col = next((i for i, h in enumerate(headers) if "name" in h.lower() or "participant" in h.lower()), -1)
        email_col = next((i for i, h in enumerate(headers) if "email" in h.lower() or "address" in h.lower()), -1)
        join_col = next((i for i, h in enumerate(headers) if "join" in h.lower() and "has joined" not in h.lower() and "joined room" not in h.lower()), -1)
        leave_col = next((i for i, h in enumerate(headers) if "leave" in h.lower() or "left" in h.lower()), -1)
        dur_col = next((i for i, h in enumerate(headers) if "duration" in h.lower()), -1)
        meeting_id_col = next((i for i, h in enumerate(headers) if "meeting id" in h.lower() or "meeting_id" in h.lower()), -1)

        if name_col == -1 or email_col == -1 or join_col == -1 or leave_col == -1:
            flash("Could not locate all required columns (Name, Email, Join/Leave Time) in the CSV.", "danger")
            return redirect(request.url)

        # Fallback to column-level Meeting ID if metadata row wasn't found
        if not meeting_id and meeting_id_col != -1:
            for row in data_rows:
                if len(row) > meeting_id_col and row[meeting_id_col].strip():
                    meeting_id = row[meeting_id_col].strip()
                    break

        if not meeting_id:
            import random
            meeting_id = str(random.randint(100000000, 9999999999))



        # Helper to parse time strings safely
        def parse_date(date_str):
            for fmt in (
                "%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %I:%M:%S %p", "%Y-%m-%d %I:%M:%S %p",
                "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %I:%M:%S %p", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"
            ):
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except ValueError:
                    continue
            return datetime.utcnow()

        # Try to parse start time from metadata or fallback to first participant's join time
        actual_start_dt = None
        if start_time_from_csv:
            try:
                actual_start_dt = parse_date(start_time_from_csv)
            except Exception:
                pass

        # Scan all rows to find the earliest Join Time and latest Leave Time
        all_event_times = []
        for row in data_rows:
            if not row or len(row) <= max(join_col, leave_col):
                continue
            join_str = row[join_col].strip()
            leave_str = row[leave_col].strip()
            
            j_dt = parse_date(join_str) if join_str else None
            l_dt = parse_date(leave_str) if leave_str else None
            
            if j_dt:
                all_event_times.append(j_dt)
            if l_dt:
                all_event_times.append(l_dt)

        if all_event_times:
            earliest_time = min(all_event_times)
            latest_time = max(all_event_times)
            
            if not actual_start_dt:
                actual_start_dt = earliest_time
            actual_end_dt = latest_time
        else:
            if not actual_start_dt:
                actual_start_dt = datetime.utcnow()
            actual_end_dt = actual_start_dt + timedelta(hours=1)

        # Determine topic from CSV metadata or default to date format
        if topic_from_csv:
            topic = topic_from_csv
        else:
            topic = f"Zoom Session ({actual_start_dt.strftime('%b %d, %Y')})"

        # Create Zoom Session
        active_course_id = flask_session.get("active_course_id")
        active_course_code = flask_session.get("active_course_code", "ALL")

        session = ZoomSession(
            meeting_id=meeting_id,
            topic=topic,
            host_email=current_user.email,
            professor_id=current_user.id,
            course_code=active_course_code,
            course_id=active_course_id,
            status="completed",
            actual_start=actual_start_dt,
            actual_end=actual_end_dt
        )
        db.session.add(session)
        db.session.flush()

        # Accumulate participant join/leave events from clean columns
        for idx, row in enumerate(data_rows):
            if not row or len(row) <= max(name_col, email_col):
                continue
            
            raw_name = row[name_col].strip()
            raw_email = row[email_col].strip().lower()
            join_str = row[join_col].strip() if len(row) > join_col else ""
            leave_str = row[leave_col].strip() if len(row) > leave_col else ""
            
            join_time = parse_date(join_str) if join_str else actual_start_dt
            leave_time = parse_date(leave_str) if leave_str else actual_start_dt
            
            from app.services.matching import normalize_name
            user_uuid = raw_email if raw_email else f"name_{normalize_name(raw_name)}"
            
            # Save Join Event
            db.session.add(ParticipantEvent(
                session_id=session.id,
                raw_name=raw_name,
                raw_email=raw_email,
                event_type="joined",
                event_timestamp=join_time,
                zoom_user_id=user_uuid
            ))
            
            # Save Leave Event
            db.session.add(ParticipantEvent(
                session_id=session.id,
                raw_name=raw_name,
                raw_email=raw_email,
                event_type="left",
                event_timestamp=leave_time,
                zoom_user_id=user_uuid
            ))

        db.session.commit()

        # Run post-processing & ML matching
        from app.services.attendance import finalize_session_attendance
        finalize_session_attendance(session.id, meeting_end_time=actual_end_dt)

        # Trigger PDF generation & email reports
        from app.services.report_gen import generate_pdf_report
        generate_pdf_report(session.id)

        # Recount stats for UI display
        records = AttendanceRecord.query.filter_by(session_id=session.id).all()
        present = sum(1 for r in records if r.is_present)
        partial = sum(1 for r in records if not r.is_present and (r.total_duration_seconds or 0) > 0)
        absent = sum(1 for r in records if not r.is_present and not r.total_duration_seconds)

        # Update ML metrics
        try:
            from app.services.ml_analytics import compute_risk_scores, cluster_students
            compute_risk_scores(current_user.id)
            cluster_students(current_user.id)
        except Exception:
            pass

        return render_template(
            "sessions/upload_csv.html",
            upload_done=True,
            session_id=session.id,
            present=present,
            partial=partial,
            absent=absent,
            errors=[]
        )

    return render_template("sessions/upload_csv.html", upload_done=False, courses=courses)

