"""
Train Anomaly Detection Model (Isolation Forest)
"""
import joblib
from sklearn.ensemble import IsolationForest

def train_anomaly_model(X, save_path="../../models/anomaly_detector.pkl"):
    model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    model.fit(X)
    joblib.dump(model, save_path)
    return model
