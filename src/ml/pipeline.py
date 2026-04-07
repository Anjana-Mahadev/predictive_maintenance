"""
ML Training Pipeline for Predictive Maintenance (AI4I Dataset)
- Loads data
- Preprocesses features
- Trains fault detection and anomaly detection models
- Saves trained models
"""
from preprocess import load_and_preprocess_data
from train_fault import train_fault_model
from train_anomaly import train_anomaly_model

if __name__ == "__main__":
    # Load and preprocess data
    X_fault, y_fault, X_anomaly = load_and_preprocess_data()

    # Train fault detection model
    fault_model = train_fault_model(X_fault, y_fault)

    # Train anomaly detection model
    anomaly_model = train_anomaly_model(X_anomaly)

    print("Training complete. Models saved to /models/")
