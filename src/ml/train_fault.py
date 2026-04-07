"""
Train Fault Detection Model (RandomForest/XGBoost)
"""
import joblib
from sklearn.ensemble import RandomForestClassifier
#from xgboost import XGBClassifier

def train_fault_model(X, y, save_path="../../models/fault_detector.pkl"):
    # model = XGBClassifier()  # Uncomment to use XGBoost
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    joblib.dump(model, save_path)
    return model
