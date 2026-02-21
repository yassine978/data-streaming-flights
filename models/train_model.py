"""
train_model.py — Member 2, Task 2.3 (Flight Data) — FIXED
Train Isolation Forest for flight anomaly detection.

Usage:
    python models/train_model.py
"""

import os
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report


SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH    = os.path.join(SCRIPT_DIR, "flight_anomaly_detector.pkl")
SCALER_PATH   = os.path.join(SCRIPT_DIR, "flight_scaler.pkl")
FEATURES_PATH = os.path.join(SCRIPT_DIR, "flight_features.json")
EVAL_PATH     = os.path.join(SCRIPT_DIR, "model_evaluation.txt")


def generate_training_data(n_samples: int = 10_000, random_state: int = 42):
    """Generate synthetic flight data for training."""
    rng = np.random.default_rng(random_state)
    n_normal   = int(n_samples * 0.99)
    n_anomaly  = n_samples - n_normal

    # ─── Normal flights (99%) ────────────────────────────────────────
    normal_velocity      = rng.normal(250, 50, n_normal)
    normal_altitude      = rng.normal(11000, 2000, n_normal)
    normal_vertical_rate = rng.normal(0, 3, n_normal)
    normal_hour          = rng.integers(0, 24, n_normal)
    normal_dow           = rng.integers(1, 8, n_normal)

    # ─── Anomalous flights (1%) ──────────────────────────────────────
    # FIX: Make sure all arrays have EXACTLY n_anomaly elements
    anom_velocity = rng.uniform(500, 900, n_anomaly)  # All supersonic
    anom_altitude = rng.uniform(15000, 20000, n_anomaly)  # All too high
    anom_vertical_rate = rng.uniform(20, 50, n_anomaly)  # All extreme climb
    anom_hour = rng.integers(0, 24, n_anomaly)
    anom_dow  = rng.integers(1, 8, n_anomaly)

    # Combine
    velocities     = np.concatenate([normal_velocity, anom_velocity])
    altitudes      = np.concatenate([normal_altitude, anom_altitude])
    vertical_rates = np.concatenate([normal_vertical_rate, anom_vertical_rate])
    hours          = np.concatenate([normal_hour, anom_hour])
    dows           = np.concatenate([normal_dow, anom_dow])
    labels         = np.array([1] * n_normal + [-1] * n_anomaly)

    # Verify all arrays are same length
    assert len(velocities) == len(altitudes) == len(vertical_rates) == len(hours) == len(dows) == len(labels)

    df = pd.DataFrame({
        "velocity":      velocities,
        "baro_altitude": altitudes,
        "vertical_rate": vertical_rates,
        "hour":          hours,
        "day_of_week":   dows,
        "label":         labels,
    })

    return df.sample(frac=1, random_state=random_state).reset_index(drop=True)


def train_anomaly_detector():
    print("=" * 55)
    print("  Flight Anomaly Detection Model Training")
    print("=" * 55)

    # 1. Data
    print("\n[1/5] Generating training data...")
    df = generate_training_data(n_samples=10_000)
    print(f"      Total: {len(df):,}  "
          f"(normal: {(df.label==1).sum():,}, "
          f"anomaly: {(df.label==-1).sum():,})")

    feature_names = ["velocity", "baro_altitude", "vertical_rate", "hour", "day_of_week"]
    X = df[feature_names].values
    y = df["label"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=(y == -1)
    )

    # 2. Scale
    print("\n[2/5] Scaling features...")
    scaler  = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    # 3. Train
    print("\n[3/5] Training Isolation Forest...")
    model = IsolationForest(
        n_estimators=200,
        contamination=0.01,
        max_features=len(feature_names),
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train_s)

    # 4. Evaluate
    print("\n[4/5] Evaluating on test set...")
    y_pred       = model.predict(X_test_s)
    anomaly_rate = (y_pred == -1).mean()

    report = classification_report(
        y_test, y_pred,
        target_names=["anomaly (-1)", "normal (1)"],
        zero_division=0,
    )
    print(report)
    print(f"Test anomaly rate: {anomaly_rate:.2%}")

    # 5. Save
    print("\n[5/5] Saving model artefacts...")
    os.makedirs(SCRIPT_DIR, exist_ok=True)

    joblib.dump(model,  MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)

    with open(FEATURES_PATH, "w") as f:
        json.dump(feature_names, f)

    eval_text = (
        "Flight Anomaly Detection Model — Evaluation\n"
        + "=" * 55 + "\n"
        + f"Model        : Isolation Forest\n"
        + f"n_estimators : 200\n"
        + f"contamination: 1%\n"
        + f"Features     : {feature_names}\n"
        + f"Train rows   : {len(X_train):,}\n"
        + f"Test  rows   : {len(X_test):,}\n\n"
        + report
        + f"\nTest anomaly rate: {anomaly_rate:.2%}\n"
    )
    with open(EVAL_PATH, "w") as f:
        f.write(eval_text)

    print(f"\n  ✅  model   → {MODEL_PATH}")
    print(f"  ✅  scaler  → {SCALER_PATH}")
    print(f"  ✅  features→ {FEATURES_PATH}")
    print(f"  ✅  eval    → {EVAL_PATH}")
    print("\nTraining complete!\n")


if __name__ == "__main__":
    train_anomaly_detector()