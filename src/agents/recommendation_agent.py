
import asyncio
from src.agents.groq_client import GroqClient

class RecommendationAgent:
	def __init__(self, memory):
		self.memory = memory
		self.llm = GroqClient()

	# (stray string removed)
	def recommend(self, sensor_row, root_cause):
		prompt = f"""
You are an AI maintenance engineer. Given the root cause: '{root_cause}', suggest 2-3 actionable maintenance recommendations as a JSON list.\n"""
		messages = [
			{"role": "system", "content": "You are an expert AI maintenance engineer."},
			{"role": "user", "content": prompt}
		]
		result = asyncio.run(self.llm.chat(messages))
		import json, re
		# Try to robustly extract JSON from LLM output
		try:
			# 1. Try to extract from ```json ... ``` code block
			match = re.search(r"```json\s*([\s\S]+?)```", result, re.IGNORECASE)
			if match:
				json_str = match.group(1).strip()
			else:
				# 2. Try to extract from any code block
				match2 = re.search(r"```[a-zA-Z]*\s*([\s\S]+?)```", result)
				if match2:
					json_str = match2.group(1).strip()
				else:
					# 3. Try to extract any JSON array in the string
					match3 = re.search(r'(\[\s*{[\s\S]+?}\s*\])', result)
					if match3:
						json_str = match3.group(1)
					else:
						json_str = result.strip()
			recs = json.loads(json_str)
			# Ensure always a list
			if isinstance(recs, dict):
				recs = [recs]
			# Only return if at least one rec has a 'Recommendation' or 'Description' key
			if isinstance(recs, list) and any(isinstance(r, dict) and ("Recommendation" in r or "Description" in r) for r in recs):
				return recs
			return ["No actionable recommendation"]
		except Exception as e:
			# Optionally log e for debugging
			return ["No actionable recommendation"]
