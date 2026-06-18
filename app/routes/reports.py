"""
EduTrack — Reports Routes
"""
import os
import logging
from flask import (Blueprint, render_template, send_from_directory,
                   abort, redirect, url_for, flash, current_app, session)
from flask_login import login_required, current_user
from app.models import AttendanceReport, ZoomSession

logger = logging.getLogger(__name__)
reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/")
@login_required
def list_reports():
    active_course_id = session.get("active_course_id")
    reports = AttendanceReport.query.join(ZoomSession).filter(
        ZoomSession.professor_id == current_user.id,
        ZoomSession.course_id == active_course_id
    ).order_by(AttendanceReport.generated_at.desc()).all()

    return render_template("reports/list.html", reports=reports)


@reports_bp.route("/<int:report_id>/pdf")
@login_required
def download_pdf(report_id):
    report = AttendanceReport.query.join(ZoomSession).filter(
        AttendanceReport.id == report_id,
        ZoomSession.professor_id == current_user.id,
    ).first_or_404()

    if not report.pdf_path:
        # Regenerate on the fly
        from app.services.report_gen import generate_pdf_report
        pdf_path = generate_pdf_report(report.session_id)
        if not pdf_path:
            flash("Failed to generate report PDF.", "danger")
            return redirect(url_for("reports.list_reports"))

    reports_dir = os.path.join(current_app.root_path, "static", "reports")
    return send_from_directory(reports_dir, report.pdf_path, as_attachment=True)


@reports_bp.route("/<int:report_id>/resend", methods=["POST"])
@login_required
def resend_report(report_id):
    report = AttendanceReport.query.join(ZoomSession).filter(
        AttendanceReport.id == report_id,
        ZoomSession.professor_id == current_user.id,
    ).first_or_404()

    try:
        from app.services.email_service import send_report_email
        success = send_report_email(report.id)
        if success:
            flash("Report email resent successfully! ✉️", "success")
        else:
            flash("Failed to send email. Check your mail settings.", "danger")
    except Exception as exc:
        logger.error(f"Resend failed for report {report_id}: {exc}")
        flash("Email send failed. Please try again later.", "danger")

    return redirect(url_for("reports.list_reports"))
