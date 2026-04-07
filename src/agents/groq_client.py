import os
import httpx

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")
# Use the resolved IP address for api.groq.com (update as needed)
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqClient:
    def __init__(self):
        self.api_key = GROQ_API_KEY
        self.model = GROQ_MODEL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def chat(self, messages, temperature=0.2):
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        print("DEBUG: Groq payload:", payload)
        async with httpx.AsyncClient() as client:
            resp = await client.post(GROQ_API_URL, headers=self.headers, json=payload, timeout=30)
            print("DEBUG: Groq response status:", resp.status_code)
            print("DEBUG: Groq response body:", resp.text)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
