"""
EduTrack — Database Seed Script
Creates test professor, 30 students, 5 past sessions with realistic attendance data.

Usage: python seed_db.py
"""
import os
import sys
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

os.environ.setdefault("FLASK_ENV", "development")

from app import create_app
from app.extensions import db
from app.models import (
    Professor, RegisteredStudent, ZoomSession,
    ParticipantEvent, AttendanceRecord, AttendanceReport, Course
)

app = create_app("development")

STUDENTS = [
    ("Mohammed Al-Rashid", "m.alrashid@university.edu", "STU001"),
    ("Sarah Johnson", "s.johnson@university.edu", "STU002"),
    ("Priya Sharma", "p.sharma@university.edu", "STU003"),
    ("Carlos Martinez", "c.martinez@university.edu", "STU004"),
    ("Aisha Hassan", "a.hassan@university.edu", "STU005"),
    ("Wei Zhang", "w.zhang@university.edu", "STU006"),
    ("James O'Brien", "j.obrien@university.edu", "STU007"),
    ("Fatima Mansour", "f.mansour@university.edu", "STU008"),
    ("Ethan Williams", "e.williams@university.edu", "STU009"),
    ("Layla Al-Ahmad", "l.alahmad@university.edu", "STU010"),
    ("Noah Davis", "n.davis@university.edu", "STU011"),
    ("Anjali Patel", "a.patel@university.edu", "STU012"),
    ("Luis Rodriguez", "l.rodriguez@university.edu", "STU013"),
    ("Maryam Yusuf", "m.yusuf@university.edu", "STU014"),
    ("Oliver Brown", "o.brown@university.edu", "STU015"),
    ("Neha Gupta", "n.gupta@university.edu", "STU016"),
    ("Ahmed Ibrahim", "a.ibrahim@university.edu", "STU017"),
    ("Emma Wilson", "e.wilson@university.edu", "STU018"),
    ("Jing Liu", "j.liu@university.edu", "STU019"),
    ("Michael Anderson", "m.anderson@university.edu", "STU020"),
    ("Rania Khalil", "r.khalil@university.edu", "STU021"),
    ("Lucas Garcia", "l.garcia@university.edu", "STU022"),
    ("Kavya Mehta", "k.mehta@university.edu", "STU023"),
    ("Omar Abdullah", "o.abdullah@university.edu", "STU024"),
    ("Isabella Thomas", "i.thomas@university.edu", "STU025"),
    ("Hassan Ali", "h.ali@university.edu", "STU026"),
    ("Sophia Taylor", "s.taylor@university.edu", "STU027"),
    ("Yusuf Nour", "y.nour@university.edu", "STU028"),
    ("Chloe Jackson", "c.jackson@university.edu", "STU029"),
    ("Ibrahim Saleh", "i.saleh@university.edu", "STU030"),
]

SESSION_TOPICS = [
    "Introduction to Machine Learning",
    "Neural Networks and Deep Learning",
    "Data Structures and Algorithms",
    "Software Engineering Principles",
    "Database Design and SQL",
]

# Zoom name variations (simulate imperfect matching)
def zoom_variation(full_name: str, email: str, index: int) -> tuple[str, str]:
    """Return a Zoom display name variation."""
    parts = full_name.split()
    variations = [
        full_name,                                   # exact
        f"{parts[0]} {parts[-1][0]}.",              # first + last initial
        f"{parts[0][0]}. {parts[-1]}",              # first initial + last
        f"{full_name} | CS301",                      # with course suffix
        f"{full_name.lower()}",                      # lowercase
        f"{parts[-1]}, {parts[0]}",                 # reversed
        f"{parts[0]}",                               # first name only
        full_name,                                   # exact again
    ]
    return variations[index % len(variations)], email if index % 3 != 0 else ""


def seed():
    with app.app_context():
        print("[*] Seeding EduTrack database...")

        # Clear existing test data
        if Professor.query.filter_by(email="dr.smith@university.edu").first():
            print("  [!] Test professor already exists. Skipping seed.")
            return

        # ── Create Professor ──────────────────────────────────────────
        prof = Professor(
            name="Dr. Jane Smith",
            email="dr.smith@university.edu",
            department="Computer Science",
        )
        prof.set_password("password123")
        db.session.add(prof)
        db.session.flush()
        print(f"  [+] Professor created: {prof.email}")

        # ── Create Courses ────────────────────────────────────────────
        c1 = Course(code="CS301", name="Advanced Algorithms & Data Structures", professor_id=prof.id)
        c2 = Course(code="CS302", name="Intro to Machine Learning", professor_id=prof.id)
        db.session.add(c1)
        db.session.add(c2)
        db.session.flush()
        print(f"  [+] Courses created: {c1.code}, {c2.code}")

        # ── Create Students ───────────────────────────────────────────
        students = []
        for i, (name, email, sid) in enumerate(STUDENTS):
            student = RegisteredStudent(
                full_name=name,
                email=email,
                student_id=sid,
                course_code="CS301",
                course_id=c1.id,
                professor_id=prof.id,
            )
            db.session.add(student)
            students.append(student)
        db.session.flush()
        print(f"  [+] {len(students)} students created.")

        db.session.commit()
        print("\n[OK] Database seeded successfully!")
        print(f"   Login: dr.smith@university.edu / password123")


if __name__ == "__main__":
    seed()
