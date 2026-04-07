from src.agents.groq_client import GroqClient

class ReasoningAgent:
    def __init__(self, memory):
        self.memory = memory
        self.llm = GroqClient()

    async def reason(self, sensor_row, context):
        import re, json
        prompt = (
            "You are an AI maintenance engineer. Given the following sensor readings and retrieved docs, reason about the most likely fault type. "
            "The ONLY valid fault types are: TWF (Total Water Failure), HDF (Heater Duty Failure), PWF (Pump Wear Failure), OSF (Outflow Sensor Failure), RNF (Reactor Noise Fault), or None.\n"
            f"Sensor data: {sensor_row}\n"
            f"Retrieved docs: {context.get('sources', [])}\n"
            "\n"
            "Respond ONLY with a valid JSON object in the following format (do not include any explanation, extra text, or generic phrases like 'Fault Detected'):\n"
            '{"fault": "<fault_type>"}'
            "\nFor example: {\"fault\": \"TWF\"} or {\"fault\": \"None\"}\n"
            "Do NOT return generic values like 'Fault Detected', 'No Fault', or any text outside the JSON.\n"
            "Negative example (do NOT do this): Fault: Fault Detected\n"
            "If the system is operating normally, always return: {\"fault\": \"None\"}"
        )
        messages = [
            {"role": "system", "content": "You are an expert AI maintenance engineer."},
            {"role": "user", "content": prompt}
        ]
        print("DEBUG: ReasoningAgent messages:", messages)
        result = await self.llm.chat(messages)
        print("DEBUG: ReasoningAgent result:", result)
        # Try to extract JSON
        extracted_fault = None
        try:
            # Try to find a JSON object in the output
            match = re.search(r'\{[^\}]*\}', result, re.DOTALL)
            if match:
                json_str = match.group(0)
                parsed = json.loads(json_str.replace("'", '"'))
                if 'fault' in parsed:
                    val = parsed['fault']
                    if val in ['TWF', 'HDF', 'PWF', 'OSF', 'RNF', 'None']:
                        extracted_fault = val
            # Try to parse as JSON directly
            if not extracted_fault:
                parsed = json.loads(result)
                if 'fault' in parsed:
                    val = parsed['fault']
                    if val in ['TWF', 'HDF', 'PWF', 'OSF', 'RNF', 'None']:
                        extracted_fault = val
        except Exception:
            pass
        # Fallback: regex for fault type
        if not extracted_fault:
            fault_types = ['TWF', 'HDF', 'PWF', 'OSF', 'RNF', 'None']
            for ft in fault_types:
                if re.search(rf"['\"]?fault['\"]?\s*[:=]\s*['\"]?{ft}['\"]?", result):
                    extracted_fault = ft
                    break
                if re.search(rf"\\b{ft}\\b", result):
                    extracted_fault = ft
                    break
        # If the LLM claims normal operation or generic output, fallback to None
        if not extracted_fault:
            if re.search(r'normal operating|no fault|functioning as intended|operating normally|no underlying issue', result, re.IGNORECASE):
                extracted_fault = 'None'
        # Final forced mapping for generic/gibberish outputs
        if not extracted_fault or re.search(r'fault detected|no fault|normal operation|functioning as intended|operating normally|no underlying issue', str(result), re.IGNORECASE):
            extracted_fault = 'None'
        print(f"DEBUG: LLM raw output: {result}\nDEBUG: Extracted fault: {extracted_fault}")
        return {'fault': extracted_fault if extracted_fault else 'Unknown'}
