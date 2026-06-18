"""
EduTrack — 3-Layer ML Student Matching Engine

Layer 1: Exact match (email primary, normalized name secondary)
Layer 2: Fuzzy match (RapidFuzz token_sort_ratio + Jaro-Winkler)
Layer 3: ML RandomForestClassifier (TF-IDF + phonetic + string features)
"""
import re
import os
import logging
import unicodedata
from typing import Optional

import joblib
import numpy as np

logger = logging.getLogger(__name__)

# ─── Model path ───────────────────────────────────────────────────────────────
_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml")
_MATCHER_PATH = os.path.join(_MODEL_DIR, "name_matcher.pkl")

_matcher_model = None  # Lazy-loaded


# ─────────────────────────────────────────────────────────────────────────────
# Text normalization helpers
# ─────────────────────────────────────────────────────────────────────────────

def normalize_name(name: str) -> str:
    """Lowercase, strip accents, remove special chars, collapse whitespace."""
    if not name:
        return ""
    # Normalize unicode (handle é, ñ, etc.)
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower()
    # Remove content in brackets/parens (e.g., "Name (CS301)" → "Name")
    name = re.sub(r"[\(\[\{][^\)\]\}]*[\)\]\}]", " ", name)
    # Remove pipe-separated suffixes (e.g., "Mo | CS301" → "Mo")
    name = re.sub(r"\|.*$", "", name)
    # Remove non-alphanumeric except spaces and hyphens
    name = re.sub(r"[^a-z0-9\s\-]", " ", name)
    # Collapse whitespace
    name = " ".join(name.split())
    return name.strip()


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def extract_display_name(zoom_name: str) -> str:
    """
    Extract the actual name from Zoom display names like:
    - "Mohammed Al-Rashid | CS301"
    - "Mo Rashid (Section A)"
    - "Dr. Smith - Host"
    """
    name = zoom_name or ""
    name = re.sub(r"\s*\|.*$", "", name)          # remove | suffix
    name = re.sub(r"\s*-\s*(host|co-host).*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"[\(\[\{][^\)\]\}]*[\)\]\}]", " ", name)
    return name.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Feature extraction for ML layer
# ─────────────────────────────────────────────────────────────────────────────

def _extract_features(zoom_name: str, zoom_email: str,
                      reg_name: str, reg_email: str) -> np.ndarray:
    """Extract feature vector for a (zoom_participant, registered_student) pair."""
    from rapidfuzz import fuzz
    import jellyfish

    zn = normalize_name(zoom_name)
    rn = normalize_name(reg_name)
    ze = normalize_email(zoom_email)
    re_ = normalize_email(reg_email)

    zn_tokens = set(zn.split())
    rn_tokens = set(rn.split())

    # Token-level features
    token_overlap = (
        len(zn_tokens & rn_tokens) / max(len(zn_tokens | rn_tokens), 1)
    )
    token_sort = fuzz.token_sort_ratio(zn, rn) / 100.0
    partial_ratio = fuzz.partial_ratio(zn, rn) / 100.0
    token_set = fuzz.token_set_ratio(zn, rn) / 100.0

    # Jaro-Winkler
    jw = jellyfish.jaro_winkler_similarity(zn, rn)

    # Levenshtein normalized
    lev = jellyfish.levenshtein_distance(zn, rn)
    max_len = max(len(zn), len(rn), 1)
    lev_norm = 1.0 - lev / max_len

    # Phonetic
    def safe_soundex(s):
        try:
            return jellyfish.soundex(s) if s else ""
        except Exception:
            return ""

    def safe_metaphone(s):
        try:
            return jellyfish.metaphone(s) if s else ""
        except Exception:
            return ""

    z_first = zn.split()[0] if zn.split() else ""
    r_first = rn.split()[0] if rn.split() else ""
    z_last = zn.split()[-1] if len(zn.split()) > 1 else ""
    r_last = rn.split()[-1] if len(rn.split()) > 1 else ""

    soundex_first = float(safe_soundex(z_first) == safe_soundex(r_first) and z_first != "")
    soundex_last = float(safe_soundex(z_last) == safe_soundex(r_last) and z_last != "")
    metaphone_match = float(safe_metaphone(zn[:10]) == safe_metaphone(rn[:10]) and zn != "")

    # Name component matches
    first_exact = float(z_first == r_first and z_first != "")
    last_exact = float(z_last == r_last and z_last != "")

    # Email features
    email_exact = float(ze == re_ and ze != "")
    email_domain = float(
        ze.split("@")[-1] == re_.split("@")[-1]
        if "@" in ze and "@" in re_ else False
    )

    return np.array([
        token_overlap, token_sort, partial_ratio, token_set,
        jw, lev_norm,
        soundex_first, soundex_last, metaphone_match,
        first_exact, last_exact,
        email_exact, email_domain,
    ], dtype=np.float32)


# ─────────────────────────────────────────────────────────────────────────────
# Model loading
# ─────────────────────────────────────────────────────────────────────────────

def load_matcher_model():
    """Load the persisted matcher model, or return None if not trained yet."""
    global _matcher_model
    if _matcher_model is not None:
        return _matcher_model

    if os.path.exists(_MATCHER_PATH):
        try:
            _matcher_model = joblib.load(_MATCHER_PATH)
            logger.info("Loaded name matcher model from disk.")
            return _matcher_model
        except Exception as exc:
            logger.error(f"Failed to load matcher model: {exc}")

    logger.warning("Name matcher model not found. Layer 3 will be skipped.")
    return None


def save_matcher_model(model):
    """Persist the matcher model to disk."""
    global _matcher_model
    os.makedirs(_MODEL_DIR, exist_ok=True)
    joblib.dump(model, _MATCHER_PATH)
    _matcher_model = model
    logger.info(f"Matcher model saved to {_MATCHER_PATH}")


# ─────────────────────────────────────────────────────────────────────────────
# Main matching function
# ─────────────────────────────────────────────────────────────────────────────

def match_participant(
    zoom_name: str,
    zoom_email: str,
    students: list,
) -> Optional[tuple]:
    """
    3-Layer Student Matching Engine:
    Layer 1: Exact Match (Email and Normalized Name must both match perfectly if email is provided)
    Layer 2: Fuzzy Match (Only when Zoom email is empty)
    Layer 3: ML Matcher (Only when Zoom email is empty)
    """
    if not students:
        return None

    clean_zoom_email = normalize_email(zoom_email)
    clean_zoom_name = normalize_name(extract_display_name(zoom_name))

    # If Zoom email is provided, we enforce strict matching (both name and email must match perfectly)
    if clean_zoom_email:
        for student in students:
            clean_stud_email = normalize_email(student.email)
            clean_stud_name = normalize_name(student.full_name)
            if clean_stud_email == clean_zoom_email and clean_stud_name == clean_zoom_name:
                return (student, 1.0, "exact")
        return None

    # If Zoom email is empty, we fall back to fuzzy/ML matching on name
    # --- Layer 2: Fuzzy Match ---
    from rapidfuzz import fuzz
    import jellyfish
    
    best_fuzzy_student = None
    best_fuzzy_score = 0.0

    for student in students:
        clean_stud_name = normalize_name(student.full_name)
        
        # Calculate Jaro-Winkler and Token Sort similarity
        jw = jellyfish.jaro_winkler_similarity(clean_zoom_name, clean_stud_name)
        token_sort = fuzz.token_sort_ratio(clean_zoom_name, clean_stud_name) / 100.0
        
        # Combined score
        score = (jw + token_sort) / 2.0
        if score > best_fuzzy_score:
            best_fuzzy_score = score
            best_fuzzy_student = student

    # If fuzzy score is very high, return it
    if best_fuzzy_student and best_fuzzy_score >= 0.85:
        return (best_fuzzy_student, best_fuzzy_score, "fuzzy")

    # --- Layer 3: ML Matcher ---
    model = load_matcher_model()
    if model is not None:
        best_ml_student = None
        best_ml_prob = 0.0
        
        for student in students:
            features = _extract_features(zoom_name, zoom_email, student.full_name, student.email).reshape(1, -1)
            pred = model.predict(features)[0]
            if pred == 1:
                try:
                    prob = model.predict_proba(features)[0][1]
                except Exception:
                    prob = 0.90
                
                if prob > best_ml_prob:
                    best_ml_prob = prob
                    best_ml_student = student
                    
        if best_ml_student and best_ml_prob >= 0.70:
            return (best_ml_student, best_ml_prob, "ml")

    return None



def add_training_pair(zoom_name: str, zoom_email: str,
                      reg_name: str, reg_email: str,
                      label: int, retrain: bool = False):
    """
    Add a confirmed (zoom, registered) pair to training data.
    Optionally retrain the model immediately (for online learning).
    """
    import json
    train_file = os.path.join(_MODEL_DIR, "train_data", "confirmed_pairs.jsonl")
    os.makedirs(os.path.dirname(train_file), exist_ok=True)

    entry = {
        "zoom_name": zoom_name,
        "zoom_email": zoom_email,
        "reg_name": reg_name,
        "reg_email": reg_email,
        "label": label,
    }
    with open(train_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    if retrain:
        from app.ml.train_matcher import train_matcher_model
        train_matcher_model()
