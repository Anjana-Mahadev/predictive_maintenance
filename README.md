---

## Overview
A modular, production-ready, agentic AI system for predictive maintenance and fault diagnosis using the AI4I/TEP dataset. Features real-time streaming, explainability, multi-agent reasoning (Groq LLM), actionable recommendations, and a modern UI.

## Key Features
- **Streaming Data Ingestion:** Real-time sensor data simulation and streaming via FastAPI.
- **ML Pipeline:** RandomForest (fault detection), IsolationForest (anomaly detection), SHAP explainability.
- **Agentic Orchestration:** LangGraph-based pipeline with Retrieval, Reasoning, Root Cause, Recommendation, Verification, Alert, Scheduling, and Incident Documentation agents.
- **RAG (Retrieval-Augmented Generation):**
  - Downloads public maintenance/fault diagnosis PDFs.
  - Chunks, embeds (all-MiniLM-L6-v2), and indexes with FAISS.
  - RetrievalAgent performs semantic search for relevant context.
- **Groq LLM Integration:** All reasoning, root cause, and recommendations powered by Groq LLM (model: llama3-70b-8192).
- **Shared Memory:** All agent outputs and incident context are coordinated in a central state for traceability and explainability.
- **Alerting:** Email alerts (rate-limited) sent to configured address on fault detection.
- **Modern UI:** Live sensor graph, incident panel, and actionable recommendations.

## Project Structure
- `src/api/` — FastAPI backend, streaming endpoints
- `src/agents/` — All agent classes (Retrieval, Reasoning, etc.)
- `src/state/` — SharedMemoryState for agent coordination
- `src/ml/` — ML pipeline, model training
- `frontend/` — Modern dashboard UI (HTML/CSS/JS)
- `scripts/` — Utilities for RAG document download and vector DB build
- `docs/rag/` — Downloaded maintenance/fault diagnosis PDFs
- `storage/` — FAISS vector DB for RAG

## Setup & Usage
1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install langchain-community sentence-transformers faiss-cpu pypdf python-dotenv
   ```
2. **Configure environment:**
   - Set Groq and SMTP credentials in `.env`:
     ```
     GROQ_API_KEY=your_groq_api_key
     GROQ_MODEL=llama3-70b-8192
     SMTP_USER=your_gmail_address@gmail.com
     SMTP_PASS=your_app_password
     ```
3. **Download RAG documents:**
   ```bash
   python scripts/download_rag_docs.py
   ```
4. **Build vector DB:**
   ```bash
   python scripts/build_rag_vector_db.py
   ```
5. **Run the app:**
   ```bash
   uvicorn src.api.main:app --reload --app-dir .
   ```
6. **Access the UI:**
   - Open the frontend in your browser (see `frontend/index.html`).

## Agentic Pipeline (LangGraph)
- Orchestrator routes data through each agent node.
- RetrievalAgent performs semantic search over FAISS vector DB.
- Reasoning, Root Cause, Recommendation, and Verification agents use Groq LLM.
- SharedMemoryState ensures all incident context is available for explainability and reporting.
- Alerts are sent via email (rate-limited to 5 minutes).

## RAG Details
- **Chunking:** Default is per-PDF page (customizable).
- **Embeddings:** sentence-transformers/all-MiniLM-L6-v2 (HuggingFace).
- **Retrieval:** Semantic similarity search (top-k) using FAISS.
- **Docs:** Downloaded from NIST, Siemens, ABB, LibreTexts, arXiv, etc.

## Customization
- Add more agents or change pipeline logic in `src/agents/orchestrator.py`.
- Add more RAG documents to `docs/rag/` and rebuild the vector DB.
- Tune alerting, UI, or ML models as needed.

## Credits
- Built with FastAPI, LangChain, FAISS, HuggingFace, Groq LLM, and modern web tech.
- For research, education, and industrial prototyping.

## System Architecture Diagram

```mermaid
flowchart TD
    subgraph Data
        A[Sensor Data Stream]
    end
    subgraph Backend
        B[FastAPI Server]
        O[Orchestrator (LangGraph)]
        B1[RetrievalAgent (RAG)]
        B2[ReasoningAgent (Groq LLM)]
        B3[RootCauseAgent (Groq LLM)]
        B4[RecommendationAgent (Groq LLM)]
        B5[VerificationAgent (Groq LLM)]
        B6[AlertAgent (Email)]
        B7[SchedulingAgent]
        B8[IncidentDocAgent]
        M[SharedMemoryState]
        V[FAISS Vector DB]
    end
    subgraph Frontend
        F1[Live Sensor Graph]
        F2[Incident Panel]
    end
    A --> B
    B --> O
    O --> B1
    B1 --> V
    B1 --> M
    B1 --> B2
    B2 --> M
    B2 --> B3
    B3 --> M
    B3 --> B4
    B4 --> M
    B4 --> B5
    B5 --> M
    B5 --> B6
    B6 --> M
    B6 --> B7
    B7 --> M
    B7 --> B8
    B8 --> M
    M -- Incident State --> F2
    A -- Live Data --> F1
    V -.-> B1
    classDef agent fill:#f9f,stroke:#333,stroke-width:2px;
    class B1,B2,B3,B4,B5,B6,B7,B8, O, M, V agent;
```

---
