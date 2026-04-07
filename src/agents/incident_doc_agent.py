

import uuid
import json
import os
from datetime import datetime

class IncidentDocAgent:
	def __init__(self, memory):
		self.memory = memory
		self.incident_dir = "incidents"
		if not os.path.exists(self.incident_dir):
			os.makedirs(self.incident_dir)

	def create(self, sensor_row, root_cause, recs, confidence):
		doc_id = str(uuid.uuid4())
		# Gather all relevant state for the incident
		incident = dict(self.memory.state)
		incident.update({
			'incident_id': doc_id,
			'timestamp': datetime.utcnow().isoformat(),
			'sensor_row': sensor_row,
			'root_cause': root_cause,
			'recommendations': recs,
			'confidence': confidence
		})
		with open(os.path.join(self.incident_dir, f'{doc_id}.json'), 'w') as f:
			json.dump(incident, f, indent=2)
		return doc_id
