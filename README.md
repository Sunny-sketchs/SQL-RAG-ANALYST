# SQL-RAG-Analyst

A hybrid SQL + RAG analytics agent that answers natural-language questions over
structured sales data and unstructured company policy documents — routing each
query to the right tool (or both) automatically.

Built with FastAPI (async), LangGraph, PostgreSQL + pgvector (via Neon), and
swappable OpenAI/Gemini LLM providers.

**Live demo:**
- Frontend: https://sql-rag-frontend.onrender.com
- Backend API: https://sql-rag-analyst.onrender.com

> Hosted on Render's free tier, which spins down after inactivity. The first
> request after idle time may take 30–60s to respond (cold start) — a
> scheduled health check keeps both the backend and database warm most of
> the time (see [Keeping the deployment warm](#keeping-the-deployment-warm)).

---

## What it does

Ask a question like:

- *"What was the total order quantity last quarter?"* → queried live against
  a Postgres sales table via LLM-generated SQL
- *"What's the commission approval threshold for discounts above 20%?"* →
  retrieved from embedded policy PDFs via pgvector similarity search
- *"Does a 25% discount comply with policy, and how many orders exceed that
  threshold in our data?"* → both tools run, results are synthesized into one
  grounded, cited answer

A LangGraph router classifies each incoming query as `sql`, `rag`, or `hybrid`
and dispatches accordingly — no manual tool selection required.

---

## Architecture

```
User query → FastAPI /ask (async)
                │
                ▼
         LangGraph router
        ╱        │        ╲
     sql        rag       hybrid
      │          │           │
  SQL tool   RAG tool   both tools
  (LLM→SQL,  (embed +   (sequential,
  validated, pgvector    shared async
  executed)  search)     session)
      ╲          │          ╱
       ╲         │         ╱
          synthesis node
        (LLM combines results,
         cites sources, grounded
         strictly to retrieved
         context)
                │
                ▼
          Final answer
```

See [`docs/architecture.md`](docs/architecture.md) for a fuller breakdown and
[`docs/design_decisions.md`](docs/design_decisions.md) for the full rationale
behind every major tradeoff.

---

## Key engineering decisions

- **SQL injection defense** — LLM-generated SQL is validated before execution:
  single-statement only, SELECT-only, keyword blocklist, automatic `LIMIT`
  injection. Verified with 16 unit tests covering malformed/malicious SQL
  patterns, plus a live adversarial test simulating prompt injection through
  the natural-language query itself — run against a disposable Neon database
  branch specifically so the test could safely attempt something destructive
  without risking real data.
- **Swappable LLM providers** — chat/generation model swaps between OpenAI and
  Gemini via a single factory function and one config value, verified working
  end-to-end through the actual pipeline (not just isolated calls). Embeddings
  are intentionally *not* swappable — see design decisions doc for why.
- **Structured logging drove real bug fixes** — request-level logging of
  LLM-generated SQL, RAG retrieval results, and execution outcomes was added
  specifically to debug eval failures with evidence instead of guesswork.
  This surfaced and fixed eight distinct real bugs during development,
  including a discount-percentage/decimal units mismatch, case-sensitive
  string matching against unknown casing, schema-absent concept
  hallucination, a broken-transaction cascade failure, malformed date SQL,
  an ambiguous revenue/profit definition, unreadable timedelta serialization,
  and an LLM grounding failure where the model answered from general training
  knowledge instead of retrieved context.
- **Eval harness with mixed grading strategy** — deterministic ground-truth
  checks (fetched live from Postgres) for factual/numeric answers, and a
  minimal single-token LLM judge only for qualitative policy answers where
  semantic judgment is genuinely needed. A standalone CSV validator script
  checks and executes every ground-truth query before an eval run, catching
  authoring mistakes (e.g. unquoted commas silently corrupting CSV columns)
  before they cause a crash mid-run.

Full rationale for every tradeoff — including the complete bug-fix trail with
before/after evidence — is documented in
[`docs/design_decisions.md`](docs/design_decisions.md).

---

## Known limitations

- **No conversational memory** — each `/ask` request is answered
  independently; the system has no awareness of previous turns in a chat
  session. Follow-up questions using pronouns or implicit references (e.g.
  "what about just the Online channel?") will not resolve correctly. This
  was a deliberate scope decision (see design decisions doc).
- **No dimension/lookup tables** — the sales dataset ships with only raw
  foreign-key-style IDs (team, customer, store, product) and no accompanying
  name tables, so analysis is ID-level only, not name-level.
- **Embedding provider is pinned to OpenAI** regardless of `LLM_PROVIDER`,
  since Gemini's embedding models use a different vector dimensionality.
- **SQL and RAG tools run independently in hybrid mode** — the SQL half
  cannot reference a fact that only exists in retrieved policy text (e.g.
  "how many orders exceed *that* threshold," where the threshold is only
  defined in a policy document). A known architectural limitation, not
  currently solved.
- **Qualitative eval grading sensitivity** — the LLM-judge grader can mark a
  factually correct answer as failing if it emphasizes a different (but
  equally valid) supporting detail than the one named in the eval's expected
  answer. Documented as a known limitation of the current eval design.

---

## Tech stack

| Layer | Technology |
|---|---|
| API | FastAPI (async), Pydantic |
| Orchestration | LangGraph |
| Database | PostgreSQL + pgvector (Neon, serverless) |
| LLMs | OpenAI (`gpt-4o-mini`) / Gemini (`gemini-2.5-flash`), swappable |
| Embeddings | OpenAI `text-embedding-3-small` |
| Frontend | Streamlit |
| Deployment | Render (backend + frontend deployed separately) |

---
## 📁 Project Structure

```text
sql-rag-analyst/
├── .github/
│   └── workflows/
│       └── keep-alive.yml         # Scheduled health checks for Render deployment
├── data/
│   ├── processed/
│   └── raw/
│       ├── policies/              # Company policy documents
│       └── us_regional_sales.csv  # Sales dataset
├── docs/
│   ├── architecture.md            # System architecture overview
│   └── design_decisions.md        # Engineering decisions & trade-offs
├── eval/
│   ├── results/                   # Evaluation reports
│   ├── eval_answers.csv           # Reference answers for evaluation
│   ├── eval_questions.csv         # SQL, RAG & Hybrid evaluation dataset
│   └── run_eval.py                # Evaluation pipeline
├── frontend/
│   └── app.py                     # Streamlit web interface
├── scripts/
│   ├── init_db.py                 # Initialize PostgreSQL schema & pgvector
│   ├── ingest_sql.py              # Load sales dataset into PostgreSQL
│   ├── ingest_documents.py        # Chunk & embed policy documents
│   └── test_gemini.py             # Gemini provider verification
├── src/
│   └── app/
│       ├── agent/                 # LangGraph workflow, routing & synthesis
│       ├── api/                   # FastAPI routes & Pydantic schemas
│       ├── db/
│       │   ├── check_db.py        # Database connection verification
│       │   ├── models.py          # SQLAlchemy ORM models
│       │   └── session.py         # Async database session
│       ├── llm/
│       │   ├── provider.py        # OpenAI / Gemini provider factory
│       │   └── token_utils.py     # Token usage utilities
│       ├── tools/                 # SQL execution & RAG retrieval tools
│       ├── usage/
│       │   └── tracker.py         # Per-user token usage & daily budget tracking
│       ├── config.py              # Application configuration
│       └── main.py                # FastAPI application entry point
├── tests/
│   └── test_sql_tool.py           # SQL guardrail & adversarial tests
├── .env.example
├── pytest.ini
├── requirements.txt
└── README.md
```
---

## Setup

### Prerequisites
- Python 3.11+
- A [Neon](https://neon.tech) Postgres database (or any Postgres 14+ with
  pgvector available)
- OpenAI API key (required); Gemini API key (optional, for provider swap)

### Install

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Configure

Copy `.env.example` to `.env` and fill in:

```
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=              # optional
LLM_PROVIDER=openai           # or "gemini"
```

### Initialize the database

```bash
python -m scripts.check_db          # verify connection before proceeding
python -m scripts.init_db            # creates schema + enables pgvector
python -m scripts.ingest_sql          # loads sales CSV into Postgres
python -m scripts.ingest_documents     # chunks + embeds policy PDFs
```

### Run locally

```bash
uvicorn src.app.main:app --reload
```

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the total order quantity across all sales?"}'
```

Frontend:

```bash
streamlit run frontend/app.py
```

---

## Testing

```bash
pytest tests/ -v -m "not live"   # fast, no external calls
pytest tests/ -v -m "live"        # includes real LLM/DB adversarial test
```

The live SQL-injection test was verified against a disposable Neon database
branch, not the main database — see design decisions doc for the full
methodology.

---

## Evaluation

```bash
python -m scripts.validate_eval_csv   # sanity-check the eval question set first
python -m eval.run_eval               # run the full eval suite
```

Runs a 50-question set spanning `sql_only`, `rag_only`, and `hybrid`
categories, grades results against ground truth (deterministic for numeric
facts, LLM-judged for qualitative ones), and writes a JSON report to
`eval/results/`.

---

## Current Accuracy

**84% (42/50) on internal eval suite** — last updated 2026-07-20

| Category | Passed |
|---|---|
| SQL-only | 18/18 (100%) |
| RAG-only | 11/17 (65%) |
| Hybrid   | 13/15 (87%) |

Up from 76% (2026-07-12) after three targeted fixes, each confirmed with
isolated before/after evidence rather than assumption:

- **Retrieval recall regression** — a prior token-optimization pass reduced
  top-k chunk retrieval from 5 to 3, which caused one correct policy chunk to
  fall outside the retrieved set. Reverted to top-k=5 after confirming the
  miss in logs.
- **Ambiguous profit definition** — SQL generation inconsistently included or
  excluded discount adjustment when computing "profit" across otherwise
  identical questions. Fixed by explicitly defining pre-discount profit as
  the default in the SQL generation prompt, matching how "revenue" was
  already defined.
- **Open-ended schedule miscounting** — the synthesis step miscounted
  policy schedules with an open-ended final period (e.g. "Month 5+") as an
  additional discrete period rather than the point a ramp completes. Fixed
  with an explicit rule in the synthesis prompt; required two iterations to
  fully resolve.

Open items:

- A router misclassification (a `rag_only` question routed to `hybrid`)
  remains unresolved.
- One hybrid failure is a confirmed instance of the documented
  [SQL/RAG independence limitation](#known-limitations): the correct answer
  requires a numeric threshold (15%) that exists only in retrieved policy
  text, but SQL generation defaulted to a different, previously-seen
  threshold (20%) instead of deriving it from the RAG context.
- A handful of eval CSV rows have mismatched or fabricated expected facts
  not present in the source policy documents, and at least one qualitative
  grading failure appears to be a stricter-than-necessary LLM-judge
  assessment of an already-correct answer — both scheduled for review.

Accuracy is tracked per commit as prompts, routing logic, and the eval
fixtures themselves are refined — see commit history for the iteration
trail.

---

## Keeping the deployment warm

Render's free tier spins down services after ~15 minutes of inactivity, and
Neon's free tier separately suspends its compute after idling. The `/health`
endpoint checks the database connection (not just the API process), so a
single scheduled ping keeps both warm:

```yaml
# .github/workflows/keep-alive.yml
name: Keep Backend Awake
on:
  schedule:
    - cron: '*/10 * * * *'
jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - run: curl -f https://sql-rag-analyst.onrender.com/health || exit 0
```

An external uptime monitor (e.g. UptimeRobot) pointed at the same `/health`
URL works equally well and is slightly more punctual than GitHub Actions'
cron scheduling.

---
