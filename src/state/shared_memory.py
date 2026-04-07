

import numpy as np
import pandas as pd
from datetime import datetime

class SharedMemoryState:
	def __init__(self):
		self.reset()

	def reset(self):
		self.state = {
			"fault": None,
			"confidence": None,
			"anomaly_score": None,
			"root_cause": None,
			"recommendations": [],
			"confidence_score": None,
			"sources": [],
			"timestamp": None,
			"window_stats": {},
			"fault_type_probs": {},
			"verification_notes": None,
			"scheduled": False,
			"alert_sent": False,
			"incident_id": None
		}

	def get(self, key, default=None):
		return self.state.get(key, default)

	def set(self, key, value):
		self.state[key] = value

	def update_window_stats(self, window_rows):
		"""
		Compute rolling statistics for each sensor in the window.
		window_rows: List[dict] or List[pd.Series]
		"""
		if not window_rows:
			self.state['window_stats'] = {}
			return
		df = pd.DataFrame(window_rows)
		stats = {}
		for col in df.columns:
			if np.issubdtype(df[col].dtype, np.number):
				stats[col] = {
					'mean': float(df[col].mean()),
					'std': float(df[col].std()),
					'min': float(df[col].min()),
					'max': float(df[col].max())
				}
		self.state['window_stats'] = stats

	def update_incident(self, **kwargs):
		"""
		Update multiple incident metrics at once.
		"""
		for k, v in kwargs.items():
			if k in self.state:
				self.state[k] = v
		# Always update timestamp
		self.state["timestamp"] = datetime.utcnow().isoformat()
