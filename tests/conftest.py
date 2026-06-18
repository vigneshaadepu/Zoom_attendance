"""
EduTrack — Test Configuration & Fixtures
"""
import os
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["FLASK_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ZOOM_WEBHOOK_SECRET_TOKEN"] = "test-secret-token"
os.environ["SECRET_KEY"] = "test-secret-key"


@pytest.fixture(scope="session")
def app():
    from app import create_app
    app = create_app("testing")
    return app


@pytest.fixture(scope="session")
def client(app):
    return app.test_client()


@pytest.fixture(scope="function")
def db(app):
    from app.extensions import db as _db
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def professor(db, app):
    from app.models import Professor
    with app.app_context():
        prof = Professor(name="Test Professor", email="test@test.edu", department="CS")
        prof.set_password("testpass123")
        db.session.add(prof)
        db.session.commit()
        return Professor.query.get(prof.id)


@pytest.fixture(scope="function")
def sample_students(db, professor, app):
    from app.models import RegisteredStudent
    with app.app_context():
        names = [
            ("Mohammed Al-Rashid", "m.alrashid@test.edu", "STU001"),
            ("Sarah Johnson", "s.johnson@test.edu", "STU002"),
            ("Priya Sharma", "p.sharma@test.edu", "STU003"),
        ]
        students = []
        for name, email, sid in names:
            s = RegisteredStudent(
                full_name=name, email=email, student_id=sid,
                course_code="CS301", professor_id=professor.id
            )
            db.session.add(s)
            students.append(s)
        db.session.commit()
        return students
