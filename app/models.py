"""
EduTrack — SQLAlchemy Models
"""
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ─────────────────────────────────────────────────────────────────────────────
# Professor
# ─────────────────────────────────────────────────────────────────────────────
class Professor(UserMixin, db.Model):
    __tablename__ = "professors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    department = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=utcnow)

    # Relationships
    students = db.relationship(
        "RegisteredStudent", back_populates="professor", lazy="dynamic",
        cascade="all, delete-orphan"
    )
    sessions = db.relationship(
        "ZoomSession", back_populates="professor", lazy="dynamic",
        cascade="all, delete-orphan"
    )
    courses = db.relationship(
        "Course", back_populates="professor", lazy="dynamic",
        cascade="all, delete-orphan"
    )

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Professor {self.email}>"


# ─────────────────────────────────────────────────────────────────────────────
# Course
# ─────────────────────────────────────────────────────────────────────────────
class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey("professors.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    # Relationships
    professor = db.relationship("Professor", back_populates="courses")
    students = db.relationship(
        "RegisteredStudent", back_populates="course", lazy="dynamic",
        cascade="all, delete-orphan"
    )
    sessions = db.relationship(
        "ZoomSession", back_populates="course", lazy="dynamic",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Course {self.code} - {self.name}>"


# ─────────────────────────────────────────────────────────────────────────────
# RegisteredStudent
# ─────────────────────────────────────────────────────────────────────────────
class RegisteredStudent(db.Model):
    __tablename__ = "registered_students"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), nullable=False, index=True)
    student_id = db.Column(db.String(50), nullable=False)
    course_code = db.Column(db.String(30), nullable=False, index=True)
    professor_id = db.Column(db.Integer, db.ForeignKey("professors.id"), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    professor = db.relationship("Professor", back_populates="students")
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=True)
    course = db.relationship("Course", back_populates="students")
    attendance_records = db.relationship(
        "AttendanceRecord", back_populates="student", lazy="dynamic",
        cascade="all, delete-orphan"
    )

    # ML cluster label
    cluster_label = db.Column(db.String(50))
    risk_score = db.Column(db.Float, default=0.0)
    risk_label = db.Column(db.String(20), default="low")  # low/medium/high

    __table_args__ = (
        db.UniqueConstraint("email", "course_code", "professor_id",
                            name="uq_student_email_course"),
    )

    def __repr__(self):
        return f"<Student {self.full_name} ({self.student_id})>"

    @property
    def attendance_rate(self):
        """Overall attendance rate across all sessions."""
        records = self.attendance_records.all()
        if not records:
            return 0.0
        present = sum(1 for r in records if r.is_present)
        return round(present / len(records) * 100, 1)

    @property
    def has_records(self):
        """Check if student has any attendance/session records in the system."""
        return self.attendance_records.first() is not None


# ─────────────────────────────────────────────────────────────────────────────
# ZoomSession
# ─────────────────────────────────────────────────────────────────────────────
class ZoomSession(db.Model):
    __tablename__ = "zoom_sessions"

    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.String(100), nullable=False, index=True)
    topic = db.Column(db.String(300))
    host_email = db.Column(db.String(120))
    scheduled_start = db.Column(db.DateTime)
    scheduled_end = db.Column(db.DateTime)
    actual_start = db.Column(db.DateTime)
    actual_end = db.Column(db.DateTime)
    professor_id = db.Column(db.Integer, db.ForeignKey("professors.id"), nullable=False)
    status = db.Column(db.String(20), default="scheduled")  # scheduled/live/completed
    course_code = db.Column(db.String(30))

    # Relationships
    professor = db.relationship("Professor", back_populates="sessions")
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=True)
    course = db.relationship("Course", back_populates="sessions")
    participant_events = db.relationship(
        "ParticipantEvent", back_populates="session", lazy="dynamic",
        cascade="all, delete-orphan"
    )
    attendance_records = db.relationship(
        "AttendanceRecord", back_populates="session", lazy="dynamic",
        cascade="all, delete-orphan"
    )
    report = db.relationship(
        "AttendanceReport", back_populates="session", uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ZoomSession {self.meeting_id} ({self.status})>"

    @property
    def duration_minutes(self):
        if self.actual_start and self.actual_end:
            delta = self.actual_end - self.actual_start
            return round(delta.total_seconds() / 60, 1)
        return None

    @property
    def attendance_percentage(self):
        records = self.attendance_records.all()
        if not records:
            return 0.0
        present = sum(1 for r in records if r.is_present)
        return round(present / len(records) * 100, 1)


# ─────────────────────────────────────────────────────────────────────────────
# AttendanceRecord
# ─────────────────────────────────────────────────────────────────────────────
class AttendanceRecord(db.Model):
    __tablename__ = "attendance_records"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("registered_students.id"), nullable=False
    )
    session_id = db.Column(
        db.Integer, db.ForeignKey("zoom_sessions.id"), nullable=False
    )
    zoom_display_name = db.Column(db.String(300))
    zoom_email = db.Column(db.String(120))
    join_time = db.Column(db.DateTime)
    leave_time = db.Column(db.DateTime)
    total_duration_seconds = db.Column(db.Integer, default=0)
    is_present = db.Column(db.Boolean, default=False, nullable=False)
    match_confidence_score = db.Column(db.Float, default=0.0)
    match_method = db.Column(db.String(20))  # exact/fuzzy/ml/manual/absent
    needs_review = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    # Relationships
    student = db.relationship("RegisteredStudent", back_populates="attendance_records")
    session = db.relationship("ZoomSession", back_populates="attendance_records")

    __table_args__ = (
        db.UniqueConstraint("student_id", "session_id", name="uq_attendance_record"),
    )

    def __repr__(self):
        status = "✓" if self.is_present else "✗"
        return f"<AttendanceRecord {status} student={self.student_id} session={self.session_id}>"

    @property
    def duration_minutes(self):
        return round(self.total_duration_seconds / 60, 1) if self.total_duration_seconds else 0

    @property
    def attendance_status(self):
        """Return: present, partial, or absent."""
        from flask import current_app
        threshold = current_app.config.get("SESSION_DURATION_THRESHOLD", 3600)
        if self.is_present:
            return "present"
        elif self.total_duration_seconds and self.total_duration_seconds > 0:
            return "partial"
        return "absent"


# ─────────────────────────────────────────────────────────────────────────────
# ParticipantEvent (raw Zoom webhook log)
# ─────────────────────────────────────────────────────────────────────────────
class ParticipantEvent(db.Model):
    __tablename__ = "participant_events"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer, db.ForeignKey("zoom_sessions.id"), nullable=False
    )
    raw_name = db.Column(db.String(300))
    raw_email = db.Column(db.String(120))
    event_type = db.Column(db.String(20), nullable=False)  # joined/left
    event_timestamp = db.Column(db.DateTime, nullable=False)
    zoom_user_id = db.Column(db.String(100))

    session = db.relationship("ZoomSession", back_populates="participant_events")

    def __repr__(self):
        return f"<ParticipantEvent {self.event_type} {self.raw_name} @ {self.event_timestamp}>"


# ─────────────────────────────────────────────────────────────────────────────
# AttendanceReport
# ─────────────────────────────────────────────────────────────────────────────
class AttendanceReport(db.Model):
    __tablename__ = "attendance_reports"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer, db.ForeignKey("zoom_sessions.id"), nullable=False, unique=True
    )
    generated_at = db.Column(db.DateTime, default=utcnow)
    pdf_path = db.Column(db.String(500))
    email_sent = db.Column(db.Boolean, default=False)
    email_sent_at = db.Column(db.DateTime)
    total_registered = db.Column(db.Integer, default=0)
    total_present = db.Column(db.Integer, default=0)
    total_absent = db.Column(db.Integer, default=0)
    average_duration_seconds = db.Column(db.Integer, default=0)

    session = db.relationship("ZoomSession", back_populates="report")

    def __repr__(self):
        return f"<AttendanceReport session={self.session_id} sent={self.email_sent}>"

    @property
    def attendance_percentage(self):
        if self.total_registered:
            return round(self.total_present / self.total_registered * 100, 1)
        return 0.0

    @property
    def total_partial(self):
        return self.total_registered - self.total_present - self.total_absent
