
import asyncio
from src.agents.groq_client import GroqClient

class VerificationAgent:
	def __init__(self, memory):
		self.memory = memory
		self.llm = GroqClient()

	def verify(self, sensor_row, recs):
		prompt = f"""
You are an AI maintenance engineer. Given the sensor readings and recommendations: {recs}, assign a confidence score (0-1) to the recommendations as a JSON: {{'confidence': <score>}}.\n"""
		messages = [{"role": "system", "content": "You are an expert AI maintenance engineer."},
					{"role": "user", "content": prompt}]
		result = asyncio.run(self.llm.chat(messages))
		import json
		try:
			conf = json.loads(result)
			return True, float(conf.get('confidence', 0.9))
		except Exception:
			return True, 0.9
