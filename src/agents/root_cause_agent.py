import asyncio
from src.agents.groq_client import GroqClient

class RootCauseAgent:
    def __init__(self, memory):
        self.memory = memory
        self.llm = GroqClient()

    def explain(self, sensor_row, reasoning):
        prompt = f"""
You are an AI maintenance engineer. Given the sensor readings and detected fault ({reasoning.get('fault','')}), explain the root cause in 1-2 sentences.\nSensor data: {sensor_row}
"""
        messages = [{"role": "system", "content": "You are an expert AI maintenance engineer."},
                    {"role": "user", "content": prompt}]
        result = asyncio.run(self.llm.chat(messages))
        return result.strip()
