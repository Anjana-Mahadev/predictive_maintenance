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

class RootCauseAgent:
    def __init__(self, memory):
        self.memory = memory
        self.llm = GroqClient()

    def explain(self, sensor_row, reasoning):
        fault = reasoning.get('fault', '')
        prompt = f"""
    {DATASET_CONTEXT}
    You are an AI maintenance engineer. Given the sensor readings and detected fault ({fault}), explain the root cause in 1-2 sentences.\nSensor data: {sensor_row}\n
    Strict requirements:
    - Your answer MUST be concise, technical, and reference only the features and failure modes in the ai4i2020 dataset.
    - Do NOT mention any process, industry, or equipment not present in the dataset.
    - Do NOT hallucinate or invent details.
    - Do NOT give generic, vague, or motivational statements.
    - If the system is normal, say so. If a fault is present, give a specific, actionable root cause for that fault type.
    - If you cannot determine a root cause, say 'Unknown root cause for {fault}'.
    """
        if fault and fault != "None":
            prompt += f"\nThe detected fault is {fault}. Provide a specific, actionable root cause for this fault type. Do NOT say the system is normal, normal operation, or anything similar."
        messages = [{"role": "system", "content": "You are an expert AI maintenance engineer."},
                    {"role": "user", "content": prompt}]
        result = asyncio.run(self.llm.chat(messages))
        # Post-process: Remove inappropriate, generic, or hallucinated answers
        bad_phrases = [
            "system is normal", "normal operation", "no fault", "functioning as intended", "operating normally", "no underlying issue",
            "as an ai language model", "i am unable", "i cannot", "motivational", "ensure safety", "consult a professional", "not enough information"
        ]
        if fault and fault != "None":
            if any(x in result.lower() for x in bad_phrases):
                return f"Root cause for {fault}: Fault detected. Please check the relevant subsystem."
        # Remove any hallucinated process/industry
        for phrase in ["Tennessee Eastman", "chemical plant", "reactor", "distillation", "boiler", "compressor", "pump station", "oil refinery", "pharmaceutical", "food processing", "AI language model"]:
            if phrase.lower() in result.lower():
                return f"Root cause for {fault}: Fault detected. Please check the relevant subsystem."
        return result.strip()
