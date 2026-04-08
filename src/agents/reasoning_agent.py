DATASET_CONTEXT = (
    "This dataset (ai4i2020) contains 10,000 rows of machine sensor/process data for predictive maintenance in a manufacturing context. "
    "Features: UID (unique id), product ID (L/M/H for quality variant), air temperature [K], process temperature [K], rotational speed [rpm], torque [Nm], tool wear [min]. "
    "The 'machine failure' label is set if any of five failure modes are true: "
    "TWF (tool wear failure: tool wear 200-240 min), HDF (heat dissipation failure: air-process temp diff <8.6K and speed <1380rpm), "
    "PWF (power failure: process power <3500W or >9000W), OSF (overstrain: tool wear*torque exceeds threshold by product type), "
    "RNF (random failure: 0.1% chance per process). "
    "If any failure mode is true, 'machine failure'=1. The dataset does not reveal which failure mode caused the failure."
)
from src.agents.groq_client import GroqClient

class ReasoningAgent:
    def __init__(self, memory):
        self.memory = memory
        self.llm = GroqClient()

    async def reason(self, sensor_row, context):
        import re, json
        prompt = (
            f"{DATASET_CONTEXT}\n"
            "You are an AI maintenance engineer. Given the following sensor readings and retrieved docs, reason about the most likely fault type. "
            "The ONLY valid fault types are: TWF, HDF, PWF, OSF, RNF, or None.\n"
            f"Sensor data: {sensor_row}\n"
            f"Retrieved docs: {context.get('sources', [])}\n"
            "\n"
            "Strict requirements:\n"
            "- Respond ONLY with a valid JSON object in the following format (no extra text, no explanation, no generic phrases):\n"
            '{"fault": "<fault_type>"}'
            "\nFor example: {\"fault\": \"TWF\"} or {\"fault\": \"None\"}\n"
            "- Do NOT return generic values like 'Fault Detected', 'No Fault', or any text outside the JSON.\n"
            "- Do NOT mention any process, industry, or equipment not present in the dataset.\n"
            "- Do NOT hallucinate or invent details.\n"
            "- Do NOT give generic, vague, or motivational statements.\n"
            "Negative example (do NOT do this): Fault: Fault Detected\n"
            "If the system is operating normally, always return: {\"fault\": \"None\"}\n"
            "\n"
            "Few-shot examples:\n"
            "Input: Sensor data: {'Air temperature [K]': 298, 'Process temperature [K]': 308, 'Rotational speed [rpm]': 1400, 'Torque [Nm]': 20, 'Tool wear [min]': 50, 'Type': 1}\nOutput: {\"fault\": \"None\"}\n"
            "Input: Sensor data: {'Air temperature [K]': 310, 'Process temperature [K]': 320, 'Rotational speed [rpm]': 2100, 'Torque [Nm]': 49, 'Tool wear [min]': 199, 'Type': 1}\nOutput: {\"fault\": \"TWF\"}\n"
        )
        messages = [
            {"role": "system", "content": "You are an expert AI maintenance engineer."},
            {"role": "user", "content": prompt}
        ]
        print("DEBUG: ReasoningAgent messages:", messages)
        result = await self.llm.chat(messages, temperature=0.1)
        print("DEBUG: ReasoningAgent result:", result)
        # Final validation: must be valid JSON with allowed fault type
        allowed_faults = ['TWF', 'HDF', 'PWF', 'OSF', 'RNF', 'None']
        extracted_fault = None
        try:
            match = re.search(r'\{[^\}]*\}', result, re.DOTALL)
            if match:
                json_str = match.group(0)
                parsed = json.loads(json_str.replace("'", '"'))
                if 'fault' in parsed and parsed['fault'] in allowed_faults:
                    extracted_fault = parsed['fault']
            if not extracted_fault:
                parsed = json.loads(result)
                if 'fault' in parsed and parsed['fault'] in allowed_faults:
                    extracted_fault = parsed['fault']
        except Exception:
            pass
        # Fallback: regex for allowed fault type
        if not extracted_fault:
            for ft in allowed_faults:
                if re.search(rf"['\"]?fault['\"]?\s*[:=]\s*['\"]?{ft}['\"]?", result):
                    extracted_fault = ft
                    break
                if re.search(rf"\\b{ft}\\b", result):
                    extracted_fault = ft
                    break
        # If output is not valid or contains forbidden phrases, fallback to 'None'
        forbidden = r'fault detected|no fault|normal operation|functioning as intended|operating normally|no underlying issue|as an ai language model|i am unable|i cannot|motivational|ensure safety|consult a professional|not enough information'
        if not extracted_fault or re.search(forbidden, str(result), re.IGNORECASE):
            extracted_fault = 'None'
        print(f"DEBUG: LLM raw output: {result}\nDEBUG: Extracted fault: {extracted_fault}")
        return {'fault': extracted_fault if extracted_fault else 'Unknown'}
