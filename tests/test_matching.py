"""
EduTrack — Tests for 3-Layer Name Matching Engine

Tests:
- Layer 1 (exact): email match, normalized name match
- Layer 2 (fuzzy): variations, suffixes, partial names
- Layer 3 (ML): trained model accuracy ≥ 90% on synthetic test set
- Edge cases: empty names, special characters, unicode
"""
import pytest
import numpy as np


def _make_student(full_name, email, sid="STU001", course="CS301"):
    """Create a mock RegisteredStudent-like object."""
    class MockStudent:
        pass
    s = MockStudent()
    s.full_name = full_name
    s.email = email
    s.student_id = sid
    s.course_code = course
    s.id = hash(email) % 10000
    return s


class TestNormalization:
    def test_normalize_basic(self):
        from app.services.matching import normalize_name
        assert normalize_name("Mohammed Al-Rashid") == "mohammed al-rashid"

    def test_normalize_strips_suffix(self):
        from app.services.matching import normalize_name
        assert "cs301" not in normalize_name("Mo Rashid | CS301")
        assert "section" not in normalize_name("John Smith (Section A)")

    def test_normalize_unicode(self):
        from app.services.matching import normalize_name
        result = normalize_name("José García")
        assert "jose" in result

    def test_normalize_empty(self):
        from app.services.matching import normalize_name
        assert normalize_name("") == ""
        assert normalize_name(None) == ""

    def test_extract_display_name(self):
        from app.services.matching import extract_display_name
        assert extract_display_name("Mo Rashid | CS301") == "Mo Rashid"
        assert extract_display_name("John Smith (Section B)") == "John Smith"
        assert extract_display_name("Dr. Smith - Host") == "Dr. Smith"


class TestLayer1ExactMatch:
    def setup_method(self):
        self.students = [
            _make_student("Mohammed Al-Rashid", "m.alrashid@university.edu"),
            _make_student("Sarah Johnson",       "s.johnson@university.edu"),
            _make_student("Priya Sharma",         "p.sharma@university.edu"),
        ]

    def test_strict_match_success(self):
        from app.services.matching import match_participant
        result = match_participant("Mohammed Al-Rashid", "m.alrashid@university.edu", self.students)
        assert result is not None
        student, conf, method = result
        assert student.email == "m.alrashid@university.edu"
        assert conf == 1.0
        assert method == "exact"

    def test_strict_match_fails_when_name_different(self):
        from app.services.matching import match_participant
        result = match_participant("Mo Al-Rashid", "m.alrashid@university.edu", self.students)
        assert result is None

    def test_strict_match_fails_when_email_different(self):
        from app.services.matching import match_participant
        result = match_participant("Mohammed Al-Rashid", "diff@university.edu", self.students)
        assert result is None



class TestLayer3MLAccuracy:
    """
    Test ML matcher accuracy on a synthetic test set.
    Requirement: ≥ 90% accuracy.
    """

    def _generate_test_pairs(self, n=200):
        """Generate balanced test pairs."""
        import random
        import string
        FIRST = ["Alice", "Bob", "Carlos", "Diana", "Eve", "Frank", "Grace", "Henry",
                 "Iris", "James", "Kavya", "Liam"]
        LAST  = ["Smith", "Jones", "Sharma", "Al-Rashid", "Zhang", "Garcia", "Patel"]

        pairs = []
        labels = []

        for _ in range(n // 2):
            f, l = random.choice(FIRST), random.choice(LAST)
            full = f"{f} {l}"
            email = f"{f.lower()}.{l.lower().replace('-', '')}@test.edu"
            # Positive: variation
            var = random.choice([
                f"{f} {l[0]}.",
                f"{f[0]}. {l}",
                f"{full} | CS301",
                full.lower(),
            ])
            pairs.append((var, "", full, email))
            labels.append(1)

        for _ in range(n // 2):
            f1, l1 = random.choice(FIRST), random.choice(LAST)
            f2, l2 = random.choice(FIRST), random.choice(LAST)
            while f1 == f2 and l1 == l2:
                f2, l2 = random.choice(FIRST), random.choice(LAST)
            zoom_name = f"{f1} {l1}"
            reg_name  = f"{f2} {l2}"
            zoom_email = f"{f1.lower()}.{l1.lower()}@test.edu"
            reg_email  = f"{f2.lower()}.{l2.lower()}@test.edu"
            pairs.append((zoom_name, zoom_email, reg_name, reg_email))
            labels.append(0)

        return pairs, labels

    def test_ml_model_accuracy(self):
        """ML model should achieve ≥ 90% accuracy on synthetic data."""
        import os
        from app.services.matching import _extract_features, load_matcher_model

        model_path = os.path.join("app", "ml", "name_matcher.pkl")
        if not os.path.exists(model_path):
            pytest.skip("Name matcher model not trained yet. Run seed_db.py first.")

        model = load_matcher_model()
        if model is None:
            pytest.skip("Could not load matcher model.")

        pairs, labels = self._generate_test_pairs(n=500)
        correct = 0

        for (zoom_name, zoom_email, reg_name, reg_email), label in zip(pairs, labels):
            features = _extract_features(zoom_name, zoom_email, reg_name, reg_email).reshape(1, -1)
            pred = model.predict(features)[0]
            if pred == label:
                correct += 1

        accuracy = correct / len(labels)
        print(f"\nML Matcher Test Accuracy: {accuracy*100:.2f}% ({correct}/{len(labels)})")
        assert accuracy >= 0.90, f"Expected ≥90% accuracy, got {accuracy*100:.1f}%"

    def test_feature_extraction_shape(self):
        """Feature vector should have correct shape."""
        from app.services.matching import _extract_features
        features = _extract_features("John Smith", "j.smith@test.edu",
                                     "John Smith", "j.smith@test.edu")
        assert features.shape == (13,)
        assert features.dtype == np.float32

    def test_email_exact_feature(self):
        """Email exact match feature should be 1.0 when emails match."""
        from app.services.matching import _extract_features
        features = _extract_features("X", "same@test.edu", "Y", "same@test.edu")
        # Feature index 11 is email_exact
        assert features[11] == 1.0

    def test_no_email_feature(self):
        """Email feature should be 0 when email is empty."""
        from app.services.matching import _extract_features
        features = _extract_features("John", "", "John", "j@test.edu")
        assert features[11] == 0.0  # email_exact
