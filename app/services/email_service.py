"""
EduTrack — Email Delivery Service
"""
import logging
import os
from datetime import datetime

from flask import current_app
from flask_mail import Message

from app.extensions import mail

logger = logging.getLogger(__name__)


def send_report_email(report_id: int, retry_count: int = 0) -> bool:
    """
    Send the attendance report PDF to the professor via email.
    Retries up to 3 times with exponential backoff (handled by Celery retry).

    Returns True on success, False on failure.
    """
    from app.models import AttendanceReport
    from app.extensions import db

    try:
        report = AttendanceReport.query.get(report_id)
        if not report:
            logger.error(f"Report {report_id} not found.")
            return False

        session = report.session
        professor = session.professor

        if not professor.email:
            logger.error(f"Professor has no email for report {report_id}.")
            return False

        # Build email
        session_date = (session.actual_start or session.scheduled_start or datetime.utcnow())
        subject = (
            f"Attendance Report — {session.course_code or 'Course'} — "
            f"{session_date.strftime('%B %d, %Y')}"
        )

        html_body = f"""
        <html><body style="font-family: Arial, sans-serif; color: #1e293b;">
        <div style="max-width:600px; margin:0 auto; padding:24px;">
            <div style="background:#1e3a5f; padding:20px; border-radius:8px 8px 0 0;">
                <h1 style="color:white; margin:0; font-size:22px;">📊 EduTrack Attendance Report</h1>
            </div>
            <div style="background:#f8fafc; padding:24px; border:1px solid #e2e8f0;">
                <p>Dear <b>{professor.name}</b>,</p>
                <p>The attendance report for your recent session is ready.</p>

                <table style="width:100%; border-collapse:collapse; margin:16px 0;">
                    <tr style="background:#1e3a5f; color:white;">
                        <th style="padding:10px; text-align:left;">Metric</th>
                        <th style="padding:10px; text-align:center;">Value</th>
                    </tr>
                    <tr style="background:#f1f5f9;">
                        <td style="padding:8px 10px;">Session</td>
                        <td style="padding:8px 10px; text-align:center;">{session.topic or 'Zoom Session'}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 10px;">Date</td>
                        <td style="padding:8px 10px; text-align:center;">{session_date.strftime('%B %d, %Y %H:%M')} UTC</td>
                    </tr>
                    <tr style="background:#f1f5f9;">
                        <td style="padding:8px 10px;">Total Registered</td>
                        <td style="padding:8px 10px; text-align:center;">{report.total_registered}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 10px; color:#22c55e; font-weight:bold;">✓ Present</td>
                        <td style="padding:8px 10px; text-align:center; color:#22c55e; font-weight:bold;">
                            {report.total_present} ({report.attendance_percentage}%)
                        </td>
                    </tr>
                    <tr style="background:#f1f5f9;">
                        <td style="padding:8px 10px; color:#ef4444; font-weight:bold;">✗ Absent</td>
                        <td style="padding:8px 10px; text-align:center; color:#ef4444; font-weight:bold;">{report.total_absent}</td>
                    </tr>
                </table>

                <p style="color:#64748b; font-size:13px;">
                    The full PDF report is attached to this email. You can also
                    download it from your EduTrack dashboard.
                </p>
            </div>
            <div style="background:#e2e8f0; padding:12px; border-radius:0 0 8px 8px; text-align:center;">
                <p style="margin:0; font-size:12px; color:#64748b;">
                    EduTrack v1.0 — Automated Attendance Management
                </p>
            </div>
        </div>
        </body></html>
        """

        msg = Message(
            subject=subject,
            recipients=[professor.email],
            html=html_body,
        )

        # Attach PDF if it exists
        if report.pdf_path:
            pdf_full_path = os.path.join(
                current_app.root_path, "static", "reports", report.pdf_path
            )
            if os.path.exists(pdf_full_path):
                with open(pdf_full_path, "rb") as f:
                    msg.attach(
                        filename=os.path.basename(pdf_full_path),
                        content_type="application/pdf",
                        data=f.read(),
                    )

        mail.send(msg)

        # Mark as sent
        report.email_sent = True
        report.email_sent_at = datetime.utcnow()
        db.session.commit()

        logger.info(f"Report email sent successfully for report {report_id} to {professor.email}")
        return True

    except Exception as exc:
        logger.error(f"Failed to send report email for report {report_id}: {exc}", exc_info=True)
        # Mark as failed
        try:
            from app.models import AttendanceReport
            from app.extensions import db
            report = AttendanceReport.query.get(report_id)
            if report:
                report.email_sent = False
                db.session.commit()
        except Exception:
            pass
        return False
