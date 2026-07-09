# SQL-RAG-Analyst 📊

A high-concurrency document intelligence and analytics platform built with **FastAPI**, **LangGraph**, and **Streamlit**. The application intelligently orchestrates agentic workflows, routing user queries dynamically between structured relational databases (Neon PostgreSQL) and unstructured corporate policy documentation.

---

## 🚀 Key Features

- **Intelligent Query Routing:** Uses an LLM router node to classify queries and dynamically branch workflows into **SQL**, **RAG**, or **Hybrid** execution paths.
- **Granular Token Budgeting:** Implements an enterprise-grade usage tracking layer using **Pydantic** and **tiktoken** to monitor, log, and enforce daily per-user token caps across all agent nodes.
- **Deterministic Guardrails:** Features compile-time SQL validation utilizing regex boundary checks to strictly permit read-only (`SELECT`) execution and automatically append safe evaluation limits (`LIMIT 100`).
- **Hybrid Context Synthesis:** Merges tabular database outputs with vectorized document chunks into a coherent, source-attributed final response.

---

## 🛠️ Technical Stack

- **Orchestration:** LangGraph, LangChain Core
- **LLM / Embeddings:** OpenAI (`gpt-4o-mini`, `text-embedding-3-small`), Google Gemini SDK
- **Backend Framework:** FastAPI (Asynchronous API Gateway), Uvicorn
- **Database & Vector Store:** Neon PostgreSQL, SQLAlchemy (AsyncEngine), `pgvector`
- **Frontend UI:** Streamlit
- **Testing & Quality:** Pytest, Pytest-asyncio

---

## 📁 Architecture Directory Structure

```text
sql-rag-analyst/
├── data/raw/             # Sales CSV & Policy text data
├── eval/                 # RAGAS-style pipeline evaluation scripts
├── frontend/
│   └── app.py            # Streamlit dashboard interface
├── scripts/              # DB initialization and data ingestion workers
├── src/
│   └── app/
│       ├── agent/        # LangGraph workflow, prompts & nodes
│       ├── api/          # FastAPI routes & Pydantic schemas
│       ├── db/           # PostgreSQL models & AsyncSession factories
│       ├── llm/          # Provider routing & token extraction
│       ├── tools/        # Safe SQL & RAG search tools
│       └── usage/        # Token budget enforcement & logging
└── tests/                # Async test suite
```

---

## 🛠️ Local Setup & Ingestion

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/sql-rag-analyst.git
cd sql-rag-analyst

python -m venv venv
source venv/bin/activate     # On Linux/macOS
# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

---

### 2. Configure Environment Variables

Create a `.env` file in the project root.

```env
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname?ssl=require
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
LLM_PROVIDER=openai
```

---

### 3. Initialize Database & Seed Data

Populate your Neon PostgreSQL instance with relational schemas and vector embeddings.

```bash
python scripts/init_db.py
python scripts/ingest_sql.py
python scripts/ingest_documents.py
```

---

### 4. Start the Application

#### Terminal 1 – FastAPI Backend

```bash
uvicorn src.app.main:app --reload --port 8000
```

#### Terminal 2 – Streamlit Frontend

```bash
streamlit run frontend/app.py
```

---

## 🌐 Deployment

The application is deployed in the **South Asia** region for low-latency access.

| Component | Service |
|----------|---------|
| **Backend** | FastAPI on Render (Singapore) |
| **Frontend** | Streamlit on Render (Singapore) |
| **Database** | Neon PostgreSQL (Serverless) |

---
