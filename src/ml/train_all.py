"""
Train and save fault detection and anomaly detection models for AI4I dataset.
"""

import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve
import matplotlib.pyplot as plt
import os
import json
from imblearn.over_sampling import SMOTE

def main():
    # Load data
    # Use absolute path based on script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, '../../data/ai4i2020.csv')
    df = pd.read_csv(os.path.abspath(data_path))
    # Drop identifiers
    df = df.drop(["UDI", "Product ID"], axis=1)
    # Encode Type (L, M, H) to integers
    if df["Type"].dtype == object or isinstance(df["Type"].iloc[0], str):
        type_map = {v: i for i, v in enumerate(sorted(df["Type"].unique()))}
        df["Type"] = df["Type"].map(type_map)
    # Features and targets
    feature_cols = [
        'Air temperature [K]', 'Process temperature [K]', 'Rotational speed [rpm]',
        'Torque [Nm]', 'Tool wear [min]', 'Type'
    ]
    X = df[feature_cols]
    y = df['Machine failure']

    # Train/test split for fault detection
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # Apply SMOTE oversampling to training data
    sm = SMOTE(random_state=42)
    X_train_res, y_train_res = sm.fit_resample(X_train, y_train)

    # Use class_weight='balanced' in RandomForest
    clf = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
    clf.fit(X_train_res, y_train_res)
    y_pred = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)[:, 1] if hasattr(clf, "predict_proba") else None

    # Metrics
    report = classification_report(y_test, y_pred, output_dict=True)
    cm = confusion_matrix(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_proba) if y_proba is not None else None
    fpr, tpr, _ = roc_curve(y_test, y_proba) if y_proba is not None else (None, None, None)

    # Save metrics to file
    metrics = {
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
        "roc_auc": roc_auc
    }
    models_dir = os.path.join(script_dir, '../../models')
    os.makedirs(models_dir, exist_ok=True)
    with open(os.path.join(models_dir, "fault_detection_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    # Optionally plot ROC curve
    if fpr is not None and tpr is not None:
        plt.figure()
        plt.plot(fpr, tpr, label=f"ROC curve (area = {roc_auc:.2f})")
        plt.plot([0, 1], [0, 1], 'k--')
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('Receiver Operating Characteristic')
        plt.legend(loc="lower right")
        plt.savefig(os.path.join(models_dir, "fault_detection_roc_curve.png"))
        plt.close()

    print("Fault Detection Classification Report (with SMOTE + class_weight):\n", classification_report(y_test, y_pred))
    print("Confusion Matrix:\n", cm)
    if roc_auc is not None:
        print(f"ROC-AUC: {roc_auc:.4f}")

    # Save fault detection model
    joblib.dump(clf, os.path.join(models_dir, "fault_detector.pkl"))

    # Train anomaly detection (unsupervised, use all data)
    iso = IsolationForest(n_estimators=100, contamination=0.01, random_state=42)
    iso.fit(X)
    joblib.dump(iso, os.path.join(models_dir, "anomaly_detector.pkl"))
    print(f"Models and metrics saved to {models_dir}")

if __name__ == "__main__":
    main()
