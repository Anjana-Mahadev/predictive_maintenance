


from src.agents.retrieval_agent import RetrievalAgent
from src.agents.reasoning_agent import ReasoningAgent
from src.agents.root_cause_agent import RootCauseAgent
from src.agents.recommendation_agent import RecommendationAgent
from src.agents.verification_agent import VerificationAgent
from src.agents.alert_agent import AlertAgent
from src.agents.scheduling_agent import SchedulingAgent
from src.agents.incident_doc_agent import IncidentDocAgent
from src.state.shared_memory import SharedMemoryState
from langgraph.graph import StateGraph
from pydantic import BaseModel


class Orchestrator:

    async def run_pipeline_debug(self, sensor_row):
        """
        Runs each agent node step by step, capturing memory state after each stage.
        Returns a list of memory state snapshots (dicts) after each agent.
        """
        import copy
        import numpy as np
        def to_native(val):
            if isinstance(val, np.generic):
                return val.item()
            if type(val).__module__ == 'numpy' and hasattr(val, 'item'):
                return val.item()
            if isinstance(val, (list, tuple)):
                return [to_native(x) for x in val]
            if isinstance(val, dict):
                return {to_native(k): to_native(v) for k, v in val.items()}
            return val

        # Fault type extraction from row
        def extract_fault_type(row):
            for col, label in zip(["TWF", "HDF", "PWF", "OSF", "RNF"], ["TWF", "HDF", "PWF", "OSF", "RNF"]):
                v = row.get(col, 0)
                try:
                    if isinstance(v, str):
                        v = int(float(v))
                except Exception:
                    v = 0
                if v == 1:
                    return label
            return "None"

        state = {"sensor_row": to_native(sensor_row)}
        memory_snapshots = []

        # 1. Retrieval
        context = self.retrieval.retrieve(state["sensor_row"])
        self.memory.update_incident(sources=context.get("sources", []))
        state["context"] = context
        memory_snapshots.append(copy.deepcopy(self.memory.state))

        # 2. Reasoning
        reasoning = await self.reasoning.reason(state["sensor_row"], state["context"])
        self.memory.update_incident(fault=reasoning.get("fault", None))
        state["reasoning"] = reasoning
        memory_snapshots.append(copy.deepcopy(self.memory.state))

        # 3. Root Cause
        root_cause = self.root_cause.explain(state["sensor_row"], state["reasoning"])
        if not root_cause or root_cause.strip() in ["", "Unknown", "N/A", "None"]:
            root_cause = "Unknown root cause"
        self.memory.update_incident(root_cause=root_cause)
        state["root_cause"] = root_cause
        memory_snapshots.append(copy.deepcopy(self.memory.state))

        # 4. Recommendation
        recs = self.recommendation.recommend(state["sensor_row"], state["root_cause"])
        if not recs or recs == ["No recommendation"] or recs == []:
            recs = ["No actionable recommendation"]
        self.memory.update_incident(recommendations=recs)
        state["recs"] = recs
        memory_snapshots.append(copy.deepcopy(self.memory.state))

        # 5. Verification
        verified, confidence = self.verification.verify(state["sensor_row"], state["recs"])
        self.memory.update_incident(confidence=confidence, confidence_score=confidence)
        fault_val = self.memory.get("fault")
        low_conf = confidence < 0.7
        no_fault = (not fault_val or (isinstance(fault_val, str) and fault_val.strip() in ["", "Unknown", "N/A", "None"]))
        stop = low_conf or no_fault
        state["confidence"] = confidence
        state["verified"] = verified
        state["stop"] = stop
        memory_snapshots.append(copy.deepcopy(self.memory.state))

        # 6. Router (skip if stop)
        if stop:
            return memory_snapshots

        # 7. Incident Doc
        doc_id = self.incident_doc.create(state["sensor_row"], state["root_cause"], state["recs"], state["confidence"])
        self.memory.update_incident(incident_id=doc_id)
        state["incident_id"] = doc_id
        memory_snapshots.append(copy.deepcopy(self.memory.state))

        # 8. Alert
        self.alert.send(state["sensor_row"], state["recs"])
        self.memory.update_incident(alert_sent=True)
        memory_snapshots.append(copy.deepcopy(self.memory.state))

        # 9. Scheduling
        self.scheduling.schedule(state["sensor_row"], state["recs"])
        self.memory.update_incident(scheduled=True)
        memory_snapshots.append(copy.deepcopy(self.memory.state))

        return memory_snapshots

    def __init__(self):
        self.memory = SharedMemoryState()
        self.retrieval = RetrievalAgent(self.memory)
        self.reasoning = ReasoningAgent(self.memory)
        self.root_cause = RootCauseAgent(self.memory)
        self.recommendation = RecommendationAgent(self.memory)
        self.verification = VerificationAgent(self.memory)
        self.alert = AlertAgent(self.memory)
        self.scheduling = SchedulingAgent(self.memory)
        self.incident_doc = IncidentDocAgent(self.memory)
        self._build_graph()



    def _build_graph(self):
        # Define state schema
        class PipelineState(BaseModel):
            sensor_row: dict
            context: dict = {}
            reasoning: dict = {}
            root_cause: str = ""
            recs: list = []
            confidence: float = 0.0
            incident_id: str = ""
            verified: bool = True
            stop: bool = False

        graph = StateGraph(PipelineState)

        def retrieval_node(state: PipelineState):
            context = self.retrieval.retrieve(state.sensor_row)
            self.memory.update_incident(sources=context.get("sources", []))
            return {"context": context}

        async def reasoning_node(state: PipelineState):
            reasoning = await self.reasoning.reason(state.sensor_row, state.context)
            self.memory.update_incident(fault=reasoning.get("fault", None))
            return {"reasoning": reasoning}

        def root_cause_node(state: PipelineState):
            root_cause = self.root_cause.explain(state.sensor_row, state.reasoning)
            print(f"DEBUG: LLM root_cause output: {root_cause}")
            if not root_cause or root_cause.strip() in ["", "Unknown", "N/A", "None"]:
                root_cause = "Unknown root cause"
            self.memory.update_incident(root_cause=root_cause)
            return {"root_cause": root_cause}

        def recommendation_node(state: PipelineState):
            recs = self.recommendation.recommend(state.sensor_row, state.root_cause)
            print(f"DEBUG: LLM recommendations output: {recs}")
            if not recs or recs == ["No recommendation"] or recs == []:
                recs = ["No actionable recommendation"]
            self.memory.update_incident(recommendations=recs)
            return {"recs": recs}

        def verification_node(state: PipelineState):
            verified, confidence = self.verification.verify(state.sensor_row, state.recs)
            self.memory.update_incident(confidence=confidence, confidence_score=confidence)
            # Router logic: if no fault or low confidence, halt pipeline
            fault_val = self.memory.get("fault")
            low_conf = confidence < 0.7
            no_fault = (not fault_val or (isinstance(fault_val, str) and fault_val.strip() in ["", "Unknown", "N/A", "None"]))
            stop = low_conf or no_fault
            return {"confidence": confidence, "verified": verified, "stop": stop}

        def router_node(state: PipelineState):
            # If stop is True, halt pipeline (no incident)
            if state.stop:
                return {"stop": True}
            return {"stop": False}

        def alert_node(state: PipelineState):
            self.alert.send(state.sensor_row, state.recs)
            self.memory.update_incident(alert_sent=True)
            return {}

        def scheduling_node(state: PipelineState):
            self.scheduling.schedule(state.sensor_row, state.recs)
            self.memory.update_incident(scheduled=True)
            return {}

        def incident_doc_node(state: PipelineState):
            doc_id = self.incident_doc.create(state.sensor_row, state.root_cause, state.recs, state.confidence)
            self.memory.update_incident(incident_id=doc_id)
            return {"incident_id": doc_id}

        graph.add_node("retrieval", retrieval_node)
        graph.add_node("reasoning", reasoning_node)
        graph.add_node("root_cause", root_cause_node)
        graph.add_node("recommendation", recommendation_node)
        graph.add_node("verification", verification_node)
        graph.add_node("router", router_node)
        graph.add_node("alert", alert_node)
        graph.add_node("scheduling", scheduling_node)
        graph.add_node("incident_doc", incident_doc_node)

        graph.add_edge("retrieval", "reasoning")
        graph.add_edge("reasoning", "root_cause")
        graph.add_edge("root_cause", "recommendation")
        graph.add_edge("recommendation", "verification")
        graph.add_edge("verification", "router")
        # Router: if stop, finish; else continue

        graph.add_conditional_edges("router", {
            "incident_doc": lambda state: not state.stop
        })
        graph.add_edge("incident_doc", "alert")
        graph.add_edge("alert", "scheduling")

        graph.set_entry_point("retrieval")
        graph.set_finish_point("router")

        self.graph = graph.compile()


    async def run_pipeline(self, sensor_row):
        import numpy as np
        def to_native(val):
            # Handle numpy scalars at any level
            if isinstance(val, np.generic):
                return val.item()
            if type(val).__module__ == 'numpy' and hasattr(val, 'item'):
                return val.item()
            if isinstance(val, (list, tuple)):
                return [to_native(x) for x in val]
            if isinstance(val, dict):
                return {to_native(k): to_native(v) for k, v in val.items()}
            return val

        # Fault type extraction from row
        def extract_fault_type(row):
            for col, label in zip(["TWF", "HDF", "PWF", "OSF", "RNF"], ["TWF", "HDF", "PWF", "OSF", "RNF"]):
                v = row.get(col, 0)
                try:
                    if isinstance(v, str):
                        v = int(float(v))
                except Exception:
                    v = 0
                if v == 1:
                    return label
            return "None"

        # Initial state
        state = {"sensor_row": to_native(sensor_row)}
        result = await self.graph.ainvoke(state)
        # Compose output from shared memory, converting numpy types recursively
        fault_val = self.memory.get("fault")
        if not fault_val or (isinstance(fault_val, str) and fault_val.strip() in ["", "Unknown", "N/A", "None"]):
            # Fallback to data-driven extraction
            fault_val = extract_fault_type(sensor_row)
        output = {
            "fault": fault_val,
            "confidence": self.memory.get("confidence"),
            "anomaly_score": sensor_row.get("anomaly_score", 0.0),
            "root_cause": self.memory.get("root_cause"),
            "recommendations": self.memory.get("recommendations"),
            "confidence_score": self.memory.get("confidence_score"),
            "sources": self.memory.get("sources"),
            "incident_id": self.memory.get("incident_id")
        }
        return to_native(output)
