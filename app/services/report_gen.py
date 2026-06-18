"""
EduTrack — PDF Report Generator (ReportLab)
"""
import os
import logging
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF

logger = logging.getLogger(__name__)

# Color palette
DARK_BLUE = colors.HexColor("#1e3a5f")
ACCENT_BLUE = colors.HexColor("#3b82f6")
SUCCESS_GREEN = colors.HexColor("#22c55e")
DANGER_RED = colors.HexColor("#ef4444")
WARNING_YELLOW = colors.HexColor("#f59e0b")
LIGHT_GRAY = colors.HexColor("#f1f5f9")
MID_GRAY = colors.HexColor("#94a3b8")


def _make_pie_chart(present: int, absent: int, partial: int) -> Drawing:
    drawing = Drawing(200, 150)
    pie = Pie()
    pie.x = 50
    pie.y = 10
    pie.width = 100
    pie.height = 100

    total = present + absent + partial
    if total == 0:
        total = 1

    pie.data = [present, absent, max(partial, 0)]
    pie.labels = [
        f"Present\n{present}",
        f"Absent\n{absent}",
        f"Partial\n{partial}",
    ]
    pie.slices[0].fillColor = SUCCESS_GREEN
    pie.slices[1].fillColor = DANGER_RED
    pie.slices[2].fillColor = WARNING_YELLOW
    pie.slices.strokeWidth = 0.5
    pie.slices.strokeColor = colors.white

    drawing.add(pie)
    return drawing


def generate_pdf_report(session_id: int) -> str | None:
    """
    Generate a PDF attendance report for the given session.
    Saves file to app/static/reports/ and returns the file path.
    """
    from flask import current_app
    from app.models import ZoomSession, AttendanceRecord, AttendanceReport
    from app.extensions import db

    try:
        session = ZoomSession.query.get(session_id)
        if not session:
            logger.error(f"Session {session_id} not found for PDF generation.")
            return None

        records = AttendanceRecord.query.filter_by(session_id=session_id).all()
        threshold = current_app.config.get("SESSION_DURATION_THRESHOLD", 3600)

        present_records = [r for r in records if r.is_present]
        absent_records = [r for r in records if not r.is_present and (r.total_duration_seconds or 0) == 0]
        partial_records = [r for r in records if not r.is_present and (r.total_duration_seconds or 0) > 0]

        total_registered = len(records)
        total_present = len(present_records)
        total_absent = len(absent_records)
        total_partial = len(partial_records)
        avg_duration = (
            sum(r.total_duration_seconds or 0 for r in records) // max(total_registered, 1)
        )

        # Output path
        reports_dir = os.path.join(current_app.root_path, "static", "reports")
        os.makedirs(reports_dir, exist_ok=True)
        filename = f"report_session_{session_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = os.path.join(reports_dir, filename)

        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "Title", parent=styles["Heading1"],
            fontSize=20, textColor=DARK_BLUE, spaceAfter=6
        )
        subtitle_style = ParagraphStyle(
            "Subtitle", parent=styles["Normal"],
            fontSize=11, textColor=MID_GRAY, spaceAfter=12
        )
        section_style = ParagraphStyle(
            "Section", parent=styles["Heading2"],
            fontSize=13, textColor=DARK_BLUE, spaceBefore=14, spaceAfter=6
        )
        normal_style = styles["Normal"]

        elements = []

        # ── Header ────────────────────────────────────────────────────────
        elements.append(Paragraph("📊 EduTrack Attendance Report", title_style))
        session_date = (session.actual_start or session.scheduled_start or datetime.utcnow())
        elements.append(Paragraph(
            f"<b>Course:</b> {session.course_code or 'N/A'} &nbsp;|&nbsp; "
            f"<b>Session:</b> {session.topic or 'Zoom Session'} &nbsp;|&nbsp; "
            f"<b>Date:</b> {session_date.strftime('%B %d, %Y %H:%M')} UTC",
            subtitle_style
        ))
        elements.append(Paragraph(
            f"<b>Professor:</b> {session.professor.name} ({session.professor.department or 'N/A'})",
            subtitle_style
        ))
        elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT_BLUE))
        elements.append(Spacer(1, 0.4 * cm))

        # ── Summary Box ───────────────────────────────────────────────────
        attendance_pct = round(total_present / max(total_registered, 1) * 100, 1)
        avg_min = avg_duration // 60

        summary_data = [
            ["Metric", "Value"],
            ["Total Registered", str(total_registered)],
            ["Present ✓", f"{total_present} ({attendance_pct}%)"],
            ["Absent ✗", str(total_absent)],
            ["Partial ⚠", str(total_partial)],
            ["Avg. Session Time", f"{avg_min} min"],
        ]
        summary_table = Table(summary_data, colWidths=[8 * cm, 7 * cm])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BACKGROUND", (0, 1), (-1, -1), LIGHT_GRAY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ("GRID", (0, 0), (-1, -1), 0.5, MID_GRAY),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.5 * cm))

        # ── Pie Chart ─────────────────────────────────────────────────────
        elements.append(Paragraph("Attendance Breakdown", section_style))
        pie_drawing = _make_pie_chart(total_present, total_absent, total_partial)
        elements.append(pie_drawing)
        elements.append(Spacer(1, 0.3 * cm))

        # ── Attendance Table ──────────────────────────────────────────────
        elements.append(Paragraph("Student Attendance Detail", section_style))

        table_data = [["#", "Student Name", "Student ID", "Duration (min)", "Status", "Confidence"]]

        # Sort: Absent first, then partial, then present
        sorted_records = sorted(
            records,
            key=lambda r: (
                2 if r.is_present else (1 if (r.total_duration_seconds or 0) > 0 else 0),
            )
        )

        row_colors = []
        for i, record in enumerate(sorted_records, 1):
            student = record.student
            duration_min = (record.total_duration_seconds or 0) // 60
            conf = f"{record.match_confidence_score:.0%}" if record.match_confidence_score else "—"

            if record.is_present:
                status = "✓ Present"
                status_color = SUCCESS_GREEN
            elif (record.total_duration_seconds or 0) > 0:
                status = "⚠ Partial"
                status_color = WARNING_YELLOW
            else:
                status = "✗ Absent"
                status_color = DANGER_RED

            # Flag low-confidence rows
            row_bg = colors.white
            if record.match_confidence_score and record.match_confidence_score < 0.9:
                row_bg = colors.HexColor("#fefce8")  # light yellow

            row_colors.append((i, row_bg))

            table_data.append([
                str(i),
                student.full_name if student else "—",
                student.student_id if student else "—",
                str(duration_min),
                status,
                conf,
            ])

        col_widths = [1.0 * cm, 6.5 * cm, 3.0 * cm, 3.0 * cm, 2.5 * cm, 2.0 * cm]
        att_table = Table(table_data, colWidths=col_widths, repeatRows=1)

        table_style = [
            ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.3, MID_GRAY),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (1, 1), (1, -1), "LEFT"),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ]

        # Color status column cells
        for i, record in enumerate(sorted_records, 1):
            if record.is_present:
                table_style.append(("TEXTCOLOR", (4, i), (4, i), SUCCESS_GREEN))
            elif (record.total_duration_seconds or 0) > 0:
                table_style.append(("TEXTCOLOR", (4, i), (4, i), WARNING_YELLOW))
            else:
                table_style.append(("TEXTCOLOR", (4, i), (4, i), DANGER_RED))

        att_table.setStyle(TableStyle(table_style))
        elements.append(att_table)
        elements.append(Spacer(1, 0.5 * cm))

        # ── Footer ────────────────────────────────────────────────────────
        elements.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
        elements.append(Spacer(1, 0.2 * cm))
        elements.append(Paragraph(
            f"Generated by EduTrack v1.0 on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
            ParagraphStyle("Footer", parent=normal_style, fontSize=8, textColor=MID_GRAY)
        ))

        doc.build(elements)

        # Update or create AttendanceReport record
        from app.extensions import db as _db
        report = AttendanceReport.query.filter_by(session_id=session_id).first()
        if not report:
            report = AttendanceReport(session_id=session_id)
            _db.session.add(report)

        report.pdf_path = filename
        report.generated_at = datetime.utcnow()
        report.total_registered = total_registered
        report.total_present = total_present
        report.total_absent = total_absent
        report.average_duration_seconds = avg_duration
        _db.session.commit()

        logger.info(f"PDF report generated: {pdf_path}")
        return pdf_path

    except Exception as exc:
        logger.error(f"PDF generation failed for session {session_id}: {exc}", exc_info=True)
        return None
