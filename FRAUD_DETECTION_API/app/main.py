import os
import joblib
import numpy as np
from fastapi import FastAPI

app = FastAPI(title="Fraud Detection API")

# --- PATH LOGIC ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "..", "model", "fraud_model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "..", "model", "scaler.pkl")

# --- LOAD ARTIFACTS ---
try:
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    print("Successfully loaded Model and Scaler")
except Exception as e:
    print(f" Critical Error loading artifacts: {e}")
    model = None
    scaler = None

@app.get("/")
def home():
    return {"status": "online", "model_loaded": model is not None}

@app.post("/predict")
def predict(data: dict):
    if not model or not scaler:
        return {"error": "Model artifacts not found on server", "status": 500}
    
    try:
        # Features expected by the model: V1, V2, V3, Amount
        raw_input = np.array([[
            data.get("v1", 0),
            data.get("v2", 0),
            data.get("v3", 0),
            data.get("amount", 0)
        ]])

        # 1. Scale input
        scaled_input = scaler.transform(raw_input)
        
        # 2. Predict probability and class
        prediction = model.predict(scaled_input)[0]
        probability = model.predict_proba(scaled_input)[0][1]

        # --- UPDATED: Standardized API Contract ---
        # We now send 'risk_score' and 'decision' to the Wallet Service
        return {
            "risk_score": round(float(probability), 4),
            "decision": "block" if prediction == 1 else "allow"
        }
        
    except Exception as e:
        return {"error": str(e)}