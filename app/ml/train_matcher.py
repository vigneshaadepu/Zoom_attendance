import os
import sys
import random
import numpy as np
from sklearn.ensemble import RandomForestClassifier

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.services.matching import _extract_features, save_matcher_model

def generate_synthetic_data(n=2000):
    FIRST = ["Alice", "Bob", "Carlos", "Diana", "Eve", "Frank", "Grace", "Henry",
             "Iris", "James", "Kavya", "Liam", "Mohammed", "Sarah", "Priya", "Chen"]
    LAST  = ["Smith", "Jones", "Sharma", "Al-Rashid", "Zhang", "Garcia", "Patel", "Johnson"]

    X = []
    y = []

    # Positive pairs
    for _ in range(n // 2):
        f, l = random.choice(FIRST), random.choice(LAST)
        full = f"{f} {l}"
        email = f"{f.lower()}.{l.lower().replace('-', '')}@university.edu"
        
        # variations
        var_name = random.choice([
            full,
            f"{f} {l[0]}.",
            f"{f[0]}. {l}",
            f"{full} | CS301",
            full.lower(),
            f"{l}, {f}",
        ])
        var_email = random.choice([email, "", email.lower()])
        
        features = _extract_features(var_name, var_email, full, email)
        X.append(features)
        y.append(1)

    # Negative pairs
    for _ in range(n // 2):
        f1, l1 = random.choice(FIRST), random.choice(LAST)
        f2, l2 = random.choice(FIRST), random.choice(LAST)
        while f1 == f2 and l1 == l2:
            f2, l2 = random.choice(FIRST), random.choice(LAST)
            
        zoom_name = f"{f1} {l1}"
        reg_name  = f"{f2} {l2}"
        zoom_email = f"{f1.lower()}.{l1.lower()}@university.edu"
        reg_email  = f"{f2.lower()}.{l2.lower()}@university.edu"
        
        features = _extract_features(zoom_name, zoom_email, reg_name, reg_email)
        X.append(features)
        y.append(0)

    return np.array(X), np.array(y)

def train_matcher_model():
    print("[*] Generating training data...")
    X, y = generate_synthetic_data(4000)
    
    print("[*] Training RandomForestClassifier...")
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    save_matcher_model(model)
    print("[OK] Model trained and saved successfully.")

if __name__ == "__main__":
    train_matcher_model()
