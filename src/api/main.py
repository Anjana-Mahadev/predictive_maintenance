



from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import joblib
import pandas as pd
import os
import time
import threading
from typing import List, Dict, Any
from fastapi.staticfiles import StaticFiles
# --- Import Orchestrator ---
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agents.orchestrator import Orchestrator

app = FastAPI(title="AI Maintenance Engineer Backend")

# Allow frontend to access API
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# --- Load Models ---
script_dir = os.path.dirname(os.path.abspath(__file__))
models_dir = os.path.abspath(os.path.join(script_dir, '../../models'))
fault_model = joblib.load(os.path.join(models_dir, 'fault_detector.pkl'))
anomaly_model = joblib.load(os.path.join(models_dir, 'anomaly_detector.pkl'))

# --- Streaming State ---
streaming = False
stream_thread = None


# --- Instantiate Orchestrator ---
orchestrator = Orchestrator()

# --- API Endpoints ---
@app.get("/stream")
async def stream_endpoint():
	def event_stream():
		normal_path = os.path.abspath(os.path.join(script_dir, '../../streaming/normal.csv'))
		fault_path = os.path.abspath(os.path.join(script_dir, '../../streaming/fault.csv'))
		normal_df = pd.read_csv(normal_path)
		fault_df = pd.read_csv(fault_path)
		features = ['Air temperature [K]', 'Process temperature [K]', 'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]', 'Type']
		n_normal = len(normal_df)
		n_fault = len(fault_df)
		idx_normal = 0
		idx_fault = 0
		count = 0
		while True:
			count += 1
			if count % 10 == 0:
				# Send a fault data point
				row = fault_df.iloc[idx_fault % n_fault]
				idx_fault += 1
			else:
				# Send a normal data point
				row = normal_df.iloc[idx_normal % n_normal]
				idx_normal += 1
			# Encode Type as int (L=0, M=1, H=2)
			data = row[features].to_dict()
			type_map = {'L': 0, 'M': 1, 'H': 2}
			if isinstance(data['Type'], str):
				data['Type'] = type_map.get(data['Type'], data['Type'])
			import json
			yield f"data: {json.dumps(data)}\n\n"
			time.sleep(1)
	return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.post("/predict")
async def predict_endpoint(payload: Dict[str, Any]):
	# Run fault detection model
	X = pd.DataFrame([payload])
	pred = fault_model.predict(X)[0]
	proba = fault_model.predict_proba(X)[0][1]
	return {"fault": int(pred), "confidence": float(proba)}

@app.post("/anomaly")
async def anomaly_endpoint(payload: Dict[str, Any]):
	# Run anomaly detection model
	X = pd.DataFrame([payload])
	score = anomaly_model.decision_function(X)[0]
	return {"anomaly_score": float(score)}

@app.post("/rag/analyze")
async def rag_analyze_endpoint(payload: Dict[str, Any]):
	import os
	print('DEBUG: GROQ_API_KEY', os.getenv('GROQ_API_KEY'))
	print('DEBUG: GROQ_MODEL', os.getenv('GROQ_MODEL'))
	# Run fault detection model first
	X = pd.DataFrame([payload])
	pred = fault_model.predict(X)[0]
	proba = fault_model.predict_proba(X)[0][1]
	if int(pred) == 1:
		# Fault detected, trigger agentic pipeline
		result = await orchestrator.run_pipeline(payload)
		fault_val = result.get("fault")
		# If ReasoningAgent returned a valid fault type, always use it
		if fault_val and isinstance(fault_val, str) and fault_val.strip() not in ["", "Unknown", "N/A", "None", "0", "0.0"]:
			result["fault"] = fault_val.strip()
		else:
			# Fallback to model's 1 if LLM failed
			result["fault"] = "Unknown"
		# Always set confidence
		result["confidence"] = float(proba) if hasattr(proba, 'item') else proba
		print(f"DEBUG: Outgoing /rag/analyze response type: {type(result)} value: {result}")
		return result
	else:
		# No fault, return healthy response
		return {
			"fault": "None",
			"confidence": float(proba),
			"anomaly_score": 0.0,
			"root_cause": "N/A",
			"recommendations": ["N/A"],
			"confidence_score": float(proba),
			"sources": [],
			"incident_id": None
		}

@app.post("/explain")
async def explain_endpoint(payload: Dict[str, Any]):
	# Placeholder for SHAP explainability
	return {"explanation": "Not implemented"}

# Serve frontend static files
frontend_dir = os.path.abspath(os.path.join(script_dir, '../../frontend'))
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
