DATASET_CONTEXT = (
	"This dataset (ai4i2020) contains 10,000 rows of machine sensor/process data for predictive maintenance in a manufacturing context. "
	"Features: UID (unique id), product ID (L/M/H for quality variant), air temperature [K], process temperature [K], rotational speed [rpm], torque [Nm], tool wear [min]. "
	"The 'machine failure' label is set if any of five failure modes are true: "
	"TWF (tool wear failure: tool wear 200-240 min), HDF (heat dissipation failure: air-process temp diff <8.6K and speed <1380rpm), "
	"PWF (power failure: process power <3500W or >9000W), OSF (overstrain: tool wear*torque exceeds threshold by product type), "
	"RNF (random failure: 0.1% chance per process). "
	"If any failure mode is true, 'machine failure'=1. The dataset does not reveal which failure mode caused the failure."
)

import asyncio
from src.agents.groq_client import GroqClient

class RecommendationAgent:
	def __init__(self, memory):
		self.memory = memory
		self.llm = GroqClient()

	def recommend(self, sensor_row, root_cause):
		fault = sensor_row.get("fault") or sensor_row.get("Fault")
		prompt = f"""
	{DATASET_CONTEXT}
	You are an AI maintenance engineer. Given the root cause: '{root_cause}', suggest 2-3 actionable maintenance recommendations as a JSON list.\n
	Strict requirements:
	- Your recommendations MUST be concise, technical, and reference only the features and failure modes in the ai4i2020 dataset.
	- Do NOT mention any process, industry, or equipment not present in the dataset.
	- Do NOT hallucinate or invent details.
	- Do NOT give generic, vague, or motivational statements.
	- If the system is normal, say so. If a fault is present, give specific, actionable recommendations for that fault type.
	- If you cannot determine recommendations, return ["Unknown recommendation for {fault}"].

	Few-shot examples:
	Input: Root cause: 'Tool wear exceeds threshold for product type.'
	Output: ["Replace the tool immediately.", "Inspect tool wear sensors for calibration.", "Schedule preventive maintenance for tool replacement."]
	Input: Root cause: 'System is normal.'
	Output: ["No maintenance required."]
	"""
		if fault and fault != "None":
			prompt += f"\nThe detected fault is {fault}. Provide recommendations specific to this fault type, even if the root cause is unclear. Do NOT say the system is normal, normal operation, or anything similar."
		messages = [
			{"role": "system", "content": "You are an expert AI maintenance engineer."},
			{"role": "user", "content": prompt}
		]
		result = asyncio.run(self.llm.chat(messages, temperature=0.1))
		import json, re
		# Final validation: must be valid JSON list of strings, no forbidden phrases
		forbidden = [
			"system is normal", "normal operation", "no fault", "functioning as intended", "operating normally", "no underlying issue",
			"as an ai language model", "i am unable", "i cannot", "motivational", "ensure safety", "consult a professional", "not enough information",
			"Tennessee Eastman", "chemical plant", "reactor", "distillation", "boiler", "compressor", "pump station", "oil refinery", "pharmaceutical", "food processing", "AI language model"
		]
		try:
			match = re.search(r"```json\s*([\s\S]+?)```", result, re.IGNORECASE)
			if match:
				json_str = match.group(1).strip()
			else:
				match2 = re.search(r"```[a-zA-Z]*\s*([\s\S]+?)```", result)
				if match2:
					json_str = match2.group(1).strip()
				else:
					match3 = re.search(r'(\[\s*{[\s\S]+?}\s*\])', result)
					if match3:
						json_str = match3.group(1)
					else:
						json_str = result.strip()
			recs = json.loads(json_str)
			# Must be a list of strings or dicts with Recommendation/Description
			if isinstance(recs, dict):
				recs = [recs]
			if isinstance(recs, list):
				# Check for forbidden phrases
				for r in recs:
					s = str(r)
					if any(f in s.lower() for f in forbidden):
						return ["No actionable recommendation"]
				# Accept if all are strings or dicts with Recommendation/Description
				if all(isinstance(r, str) or (isinstance(r, dict) and ("Recommendation" in r or "Description" in r)) for r in recs):
					return recs
			return ["No actionable recommendation"]
		except Exception:
			return ["No actionable recommendation"]
