"""
Preprocessing for Predictive Maintenance ML Pipeline
- Loads AI4I dataset
- Cleans and preprocesses features
- Returns data for fault and anomaly models
"""
import pandas as pd
import numpy as np

def load_and_preprocess_data(path="../../data/ai4i_dataset.csv"):
    df = pd.read_csv(path)
    # Basic cleaning
    df = df.dropna()
    # Feature engineering (example: drop non-numeric, encode type)
    if 'Type' in df.columns:
        df['Type'] = df['Type'].astype(int)
    features = ['Air temperature [K]', 'Process temperature [K]', 'Rotational speed [rpm]',
                'Torque [Nm]', 'Tool wear [min]', 'Type']
    X = df[features]
    y = df['Machine failure']
    # For anomaly detection, use only features
    return X, y, X.copy()
