from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Course, RegisteredStudent, ZoomSession

courses_bp = Blueprint("courses", __name__, url_prefix="/courses")

@courses_bp.route("/")
@login_required
def list_courses():
    courses = Course.query.filter_by(professor_id=current_user.id).all()
    course_data = []
    for c in courses:
        student_count = RegisteredStudent.query.filter_by(course_id=c.id, is_active=True).count()
        session_count = ZoomSession.query.filter_by(course_id=c.id).count()
        course_data.append({
            "course": c,
            "student_count": student_count,
            "session_count": session_count
        })
    return render_template("courses/list.html", courses=course_data)

@courses_bp.route("/create", methods=["POST"])
@login_required
def create_course():
    code = request.form.get("code", "").strip().upper()
    name = request.form.get("name", "").strip()
    
    if not code or not name:
        flash("Course code and title are required.", "danger")
        return redirect(url_for("courses.list_courses"))
        
    existing = Course.query.filter_by(code=code, professor_id=current_user.id).first()
    if existing:
        flash(f"A course with code {code} already exists.", "warning")
        return redirect(url_for("courses.list_courses"))
        
    try:
        new_course = Course(code=code, name=name, professor_id=current_user.id)
        db.session.add(new_course)
        db.session.commit()
        flash(f"Course {code} created successfully.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Failed to create course: {exc}", "danger")
        
    return redirect(url_for("courses.list_courses"))

@courses_bp.route("/<int:course_id>/select")
@login_required
def select_course(course_id):
    course = Course.query.filter_by(id=course_id, professor_id=current_user.id).first_or_404()
    session["active_course_id"] = course.id
    session["active_course_code"] = course.code
    session["active_course_name"] = course.name
    flash(f"Switched to course {course.code}.", "success")
    return redirect(url_for("dashboard.dashboard"))

@courses_bp.route("/clear")
@login_required
def clear_course():
    session.pop("active_course_id", None)
    session.pop("active_course_code", None)
    session.pop("active_course_name", None)
    return redirect(url_for("courses.list_courses"))

@courses_bp.route("/<int:course_id>/delete", methods=["POST"])
@login_required
def delete_course(course_id):
    course = Course.query.filter_by(id=course_id, professor_id=current_user.id).first_or_404()
    try:
        # If deleted course was active, clear it from session
        if session.get("active_course_id") == course.id:
            session.pop("active_course_id", None)
            session.pop("active_course_code", None)
            session.pop("active_course_name", None)
            
        db.session.delete(course)
        db.session.commit()
        flash(f"Course {course.code} deleted successfully.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Failed to delete course: {exc}", "danger")
        
    return redirect(url_for("courses.list_courses"))
