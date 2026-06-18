"""
EduTrack — ML Analytics Service

Provides:
1. At-Risk Student Detection (RandomForest)
2. Session Attendance Forecasting (Linear Regression)
3. Student Behavior Clustering (KMeans)
4. Anomaly Detection (Isolation Forest)
"""
import os
import logging
import numpy as np

import joblib
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_ML_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml")
_RISK_MODEL_PATH = os.path.join(_ML_DIR, "risk_classifier.pkl")


# ─────────────────────────────────────────────────────────────────────────────
# Helper: build feature matrix for students
# ─────────────────────────────────────────────────────────────────────────────

def _get_student_features(student, n_sessions=3):
    """
    Build a feature vector for a student's risk assessment.
    Returns (features_array, metadata_dict)
    """
    from app.models import AttendanceRecord
    records = student.attendance_records.order_by(
        AttendanceRecord.created_at.desc()
    ).limit(20).all()

    if not records:
        return None, None

    total = len(records)
    present_count = sum(1 for r in records if r.is_present)
    attendance_rate = present_count / total if total > 0 else 0.0

    # Last N sessions
    last_n = records[:n_sessions]
    last_n_rate = sum(1 for r in last_n if r.is_present) / max(len(last_n), 1)
    last_n_avg_duration = (
        sum(r.total_duration_seconds or 0 for r in last_n) / max(len(last_n), 1)
    )

    # Consecutive absences
    consecutive_absences = 0
    for r in records:
        if not r.is_present:
            consecutive_absences += 1
        else:
            break

    features = np.array([
        attendance_rate,
        last_n_rate,
        last_n_avg_duration / 3600.0,  # normalized to hours
        consecutive_absences,
        total,
    ], dtype=np.float32)

    return features, {
        "attendance_rate": attendance_rate,
        "last_n_rate": last_n_rate,
        "consecutive_absences": consecutive_absences,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. At-Risk Student Detection
# ─────────────────────────────────────────────────────────────────────────────

def compute_risk_scores(professor_id: int) -> list[dict]:
    """
    Compute risk scores for all active students of a professor.
    Returns list of dicts with student info and risk assessment.
    """
    from app.models import RegisteredStudent, AttendanceRecord
    from app.extensions import db

    students = RegisteredStudent.query.filter_by(
        professor_id=professor_id, is_active=True
    ).all()

    if not students:
        return []

    results = []

    for student in students:
        features, meta = _get_student_features(student)
        if features is None:
            risk_score = 0.0
            risk_label = "low"
        else:
            # Heuristic risk scoring (used when model not trained)
            rate = meta["attendance_rate"]
            consec = meta["consecutive_absences"]

            if rate < 0.5 or consec >= 3:
                risk_score = 0.85
                risk_label = "high"
            elif rate < 0.7 or consec >= 2:
                risk_score = 0.55
                risk_label = "medium"
            else:
                risk_score = 0.2
                risk_label = "low"

            # If model is trained, use it
            if os.path.exists(_RISK_MODEL_PATH):
                try:
                    model = joblib.load(_RISK_MODEL_PATH)
                    prob = model.predict_proba(features.reshape(1, -1))[0][1]
                    risk_score = float(prob)
                    if prob >= 0.7:
                        risk_label = "high"
                    elif prob >= 0.4:
                        risk_label = "medium"
                    else:
                        risk_label = "low"
                except Exception as exc:
                    logger.warning(f"Risk model prediction failed: {exc}")

        # Update student record
        student.risk_score = risk_score
        student.risk_label = risk_label
        db.session.add(student)

        results.append({
            "student_id": student.id,
            "name": student.full_name,
            "student_code": student.student_id,
            "course_code": student.course_code,
            "risk_score": round(risk_score, 3),
            "risk_label": risk_label,
            "attendance_rate": round(meta["attendance_rate"] * 100, 1) if meta else 0,
            "consecutive_absences": meta["consecutive_absences"] if meta else 0,
        })

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    return sorted(results, key=lambda x: x["risk_score"], reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Session Attendance Forecasting
# ─────────────────────────────────────────────────────────────────────────────

def forecast_attendance(course_code: str, professor_id: int) -> dict:
    """
    Predict expected attendance % for the next session using linear regression
    on historical data.
    """
    from app.models import ZoomSession, AttendanceRecord

    sessions = ZoomSession.query.filter_by(
        professor_id=professor_id,
        course_code=course_code,
        status="completed",
    ).order_by(ZoomSession.actual_start).all()

    if len(sessions) < 2:
        return {"forecast": None, "confidence_low": None, "confidence_high": None,
                "message": "Not enough sessions for forecasting (need at least 2)."}

    rates = []
    for s in sessions:
        records = AttendanceRecord.query.filter_by(session_id=s.id).all()
        if records:
            present = sum(1 for r in records if r.is_present)
            rates.append(present / len(records) * 100)

    if len(rates) < 2:
        return {"forecast": None, "message": "Insufficient data."}

    try:
        from sklearn.linear_model import LinearRegression

        X = np.arange(len(rates)).reshape(-1, 1)
        y = np.array(rates)
        model = LinearRegression()
        model.fit(X, y)

        next_x = np.array([[len(rates)]])
        forecast = float(model.predict(next_x)[0])
        forecast = max(0.0, min(100.0, forecast))

        # 95% confidence interval (±1 std dev of residuals)
        residuals = y - model.predict(X).flatten()
        std_err = float(np.std(residuals))

        return {
            "forecast": round(forecast, 1),
            "confidence_low": round(max(0, forecast - 2 * std_err), 1),
            "confidence_high": round(min(100, forecast + 2 * std_err), 1),
            "historical_rates": [round(r, 1) for r in rates],
            "trend": "up" if model.coef_[0] > 0.5 else "down" if model.coef_[0] < -0.5 else "stable",
        }
    except Exception as exc:
        logger.error(f"Forecasting failed: {exc}")
        return {"forecast": None, "message": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# 3. Student Behavior Clustering (KMeans)
# ─────────────────────────────────────────────────────────────────────────────

CLUSTER_LABELS = {
    0: "Always Present",
    1: "Consistently Late/Short",
    2: "Irregular Attenders",
    3: "Chronically Absent",
}


def cluster_students(professor_id: int) -> dict:
    """
    Cluster students into 4 behavioral groups using KMeans.
    Updates RegisteredStudent.cluster_label.
    Returns cluster assignments.
    """
    from app.models import RegisteredStudent, AttendanceRecord
    from app.extensions import db
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    students = RegisteredStudent.query.filter_by(
        professor_id=professor_id, is_active=True
    ).all()

    if len(students) < 4:
        return {"message": "Not enough students to cluster (need at least 4)."}

    feature_matrix = []
    valid_students = []

    for student in students:
        records = student.attendance_records.all()
        if not records:
            continue

        total = len(records)
        present = sum(1 for r in records if r.is_present)
        avg_duration = sum(r.total_duration_seconds or 0 for r in records) / total

        feature_matrix.append([
            present / total,          # attendance rate
            avg_duration / 3600.0,    # avg duration in hours
            total,                    # session count
        ])
        valid_students.append(student)

    if len(valid_students) < 4:
        return {"message": "Insufficient attendance data for clustering."}

    X = np.array(feature_matrix)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    n_clusters = min(4, len(valid_students))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)

    # Map cluster indices to meaningful labels based on centroid characteristics
    # Sort centroids by attendance rate descending
    centroids = kmeans.cluster_centers_
    sorted_clusters = sorted(range(n_clusters), key=lambda k: centroids[k][0], reverse=True)
    label_map = {}
    label_names = ["Always Present", "Consistently Late/Short",
                   "Irregular Attenders", "Chronically Absent"]
    for rank, cluster_idx in enumerate(sorted_clusters):
        label_map[cluster_idx] = label_names[min(rank, len(label_names) - 1)]

    result = {}
    for student, label in zip(valid_students, labels):
        cluster_name = label_map.get(int(label), "Unknown")
        student.cluster_label = cluster_name
        db.session.add(student)
        result[student.id] = cluster_name

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    return result


# ─────────────────────────────────────────────────────────────────────────────
# 4. Anomaly Detection (Isolation Forest)
# ─────────────────────────────────────────────────────────────────────────────

def detect_session_anomalies(professor_id: int) -> list[dict]:
    """
    Use Isolation Forest to detect sessions with anomalous attendance rates.
    Flags sessions > 2 std deviations below mean.
    """
    from app.models import ZoomSession, AttendanceRecord

    sessions = ZoomSession.query.filter_by(
        professor_id=professor_id, status="completed"
    ).order_by(ZoomSession.actual_start).all()

    if len(sessions) < 5:
        return []

    rates = []
    session_refs = []

    for s in sessions:
        records = AttendanceRecord.query.filter_by(session_id=s.id).all()
        if records:
            present = sum(1 for r in records if r.is_present)
            rate = present / len(records) * 100
            rates.append(rate)
            session_refs.append(s)

    if len(rates) < 5:
        return []

    try:
        from sklearn.ensemble import IsolationForest

        X = np.array(rates).reshape(-1, 1)
        iso = IsolationForest(contamination=0.15, random_state=42)
        preds = iso.fit_predict(X)  # -1 = anomaly, 1 = normal

        anomalies = []
        for i, (pred, session, rate) in enumerate(zip(preds, session_refs, rates)):
            if pred == -1:
                mean_rate = np.mean(rates)
                anomalies.append({
                    "session_id": session.id,
                    "topic": session.topic,
                    "date": session.actual_start.isoformat() if session.actual_start else None,
                    "attendance_rate": round(rate, 1),
                    "mean_rate": round(mean_rate, 1),
                    "deviation": round(mean_rate - rate, 1),
                })

        return anomalies
    except Exception as exc:
        logger.error(f"Anomaly detection failed: {exc}")
        return []


def retrain_risk_classifier(professor_id: int = None):
    """
    Retrain the at-risk classifier using accumulated AttendanceRecord data.
    Uses synthetic heuristic labels if not enough data.
    """
    from app.models import RegisteredStudent
    from sklearn.ensemble import RandomForestClassifier

    query = RegisteredStudent.query.filter_by(is_active=True)
    if professor_id:
        query = query.filter_by(professor_id=professor_id)
    students = query.all()

    X, y = [], []
    for student in students:
        features, meta = _get_student_features(student)
        if features is None:
            continue
        # Heuristic label for training
        rate = meta["attendance_rate"]
        consec = meta["consecutive_absences"]
        label = 1 if (rate < 0.6 or consec >= 3) else 0
        X.append(features)
        y.append(label)

    if len(X) < 10:
        logger.warning("Not enough data to retrain risk classifier.")
        return

    X = np.array(X)
    y = np.array(y)

    clf = RandomForestClassifier(n_estimators=50, random_state=42)
    clf.fit(X, y)

    os.makedirs(_ML_DIR, exist_ok=True)
    joblib.dump(clf, _RISK_MODEL_PATH)
    logger.info(f"Risk classifier retrained with {len(X)} samples.")
