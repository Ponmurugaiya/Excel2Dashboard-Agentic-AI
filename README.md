# AI BI Dashboard Builder

Upload a CSV or Excel file and get a fully designed, interactive BI dashboard — powered by a multi-agent AI pipeline that cleans your data, plans the analysis, runs the code, validates the results, and composes the layout.

![Version](https://img.shields.io/badge/version-2.0.0-blue) ![Python](https://img.shields.io/badge/python-3.11+-green) ![React](https://img.shields.io/badge/react-18-61DAFB)

---

## How it works

The system runs six specialised agents in sequence. Each agent has its own memory, a set of tools it calls in a loop, and communicates with others through a shared message bus.

```
Upload File
    │
    ▼
┌─────────────┐
│   Cleaner   │  Detects quality issues, proposes fixes, applies rules, derives columns
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Strategist  │  Profiles the data, uses LLM to plan which analyses are worth running
└──────┬──────┘
       │
       ▼
┌──────────────────────────────┐
│  Data Scientist  ║  Quality  │  Run concurrently per task — Scientist writes + executes
│  (code gen loop) ║  (review) │  code in a sandbox; Quality accepts, flags, or rejects
└──────────────────────────────┘
       │
       ▼
┌─────────────┐
│   Insight   │  Reads accepted results, generates business narrative and recommendations
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Architect  │  Ranks results, plans tab structure (LLM), composes layout, self-critiques
└──────┬──────┘
       │
       ▼
  Dashboard Spec → Frontend Renderer
```

### What makes these agents, not just LLM calls

- **Per-agent memory** — each agent accumulates short-term (key-value) and long-term (timestamped event log) state across a run. The Cleaner remembers every rule it applied; the Quality agent tracks failure patterns.
- **Goal-directed tool loops** — agents don't fire a single prompt. The Cleaner runs `detect_rules → propose_rule → apply_rule → verify`. The Architect runs `rank → plan_tabs → compose → self_review → apply_critique`.
- **Self-critique** — the Architect reads its own output, identifies issues (missing KPIs, empty tabs), and fixes them before returning.
- **Inter-agent gating** — the Quality agent can reject a Data Scientist result, preventing it from ever reaching the Architect or Insight agents.
- **Async pause/resume** — in Collaborative mode the entire pipeline suspends on `asyncio.Event` while waiting for a human decision, then resumes from exactly where it stopped.
- **Concurrent execution** — the Data Scientist runs up to 4 analysis tasks in parallel using `asyncio.Semaphore`, cutting total latency significantly.

---

## Modes

### Collaborative
The pipeline pauses at every meaningful decision point and presents a question card to the user. Decisions include: which cleaning rules to apply, whether to proceed with all analyses or priority-only, and whether to include borderline-quality results.

### Autonomous
The pipeline runs end-to-end without pausing. Each agent picks its own best answer and logs the decision with its reasoning. All auto-decisions are attached to the final dashboard spec.

---

## LLM routing

The system uses task-based model routing with automatic fallback. When a model hits a rate limit it is cooled down for 3 minutes and the next model in the chain is tried.

| Task | Primary | Fallbacks |
|------|---------|-----------|
| `planning` | Gemini 2.5 Flash | Qwen3-32B → Qwen3.6-27B → Llama 3.3-70B |
| `json` | Qwen3-32B | Qwen3.6-27B → Llama 3.3-70B → Gemini 2.5 Flash |
| `code` | Llama 3.3-70B | Qwen3.6-27B → Qwen3-32B → Gemini 2.5 Flash |
| `classify` | Llama 3.1-8B | Llama 3.3-70B |
| `chat` | Llama 3.3-70B | Qwen3-32B → Gemini 2.5 Flash |

---

## Supported analyses

| Pattern | What it produces |
|---------|-----------------|
| KPI overview | Headline metrics: total revenue, unique customers, transactions, AOV |
| Time series | Revenue / metric over time (line chart) |
| Ranking | Top N categories, products, or regions by value (bar chart) |
| RFM segmentation | Customer scoring by Recency, Frequency, Monetary → Champion / Loyal / At Risk / Lost |
| Cohort retention | Heatmap of month-by-month retention per acquisition cohort |
| Geographic | Revenue or metric by country / region (bar chart) |
| Distribution | Histogram of any numeric column |

---

## Supported file formats

- Excel: `.xlsx`, `.xls`, `.xlsm`
- CSV: `.csv`
- Max file size: 50 MB

---

## Tech stack

**Backend**
- Python 3.11+
- FastAPI + Uvicorn
- Pandas for data processing
- Plotly for chart spec generation
- Google Generative AI SDK (Gemini)
- Groq SDK (Llama, Qwen3)
- Server-Sent Events for real-time agent log streaming

**Frontend**
- React 18 + Vite
- Tailwind CSS
- Plotly.js for chart rendering
- Axios for API calls
- Lucide React for icons

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- A [Gemini API key](https://aistudio.google.com/app/apikey) (free)
- A [Groq API key](https://console.groq.com/keys) (free, recommended for fallback)

### 1. Clone and configure

```bash
git clone <repo-url>
cd AI-BI-Dashboard-Builder
```

Copy the environment template and fill in your keys:

```bash
cp .env.example .env
```

```env
# Required
GEMINI_API_KEY=AIza...

# Recommended (fallback when Gemini hits rate limits)
GROQ_API_KEY=gsk_...

# Optional — defaults shown
GEMINI_MODEL=gemini-2.5-flash
GROQ_MODEL=llama-3.3-70b-versatile
JWT_SECRET=change-me-in-production-please
```

### 2. Backend

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

pip install -r requirements.txt

uvicorn main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at **http://localhost:3000**. The Vite dev server proxies all API calls to `http://localhost:8000`.

---

## API reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health check |
| `GET` | `/health/llm` | Model routing and quota status |
| `POST` | `/upload` | Upload a data file, returns `file_path` |
| `POST` | `/analyse` | Start agent pipeline, returns `session_id` |
| `GET` | `/analyse/{id}/events` | SSE stream of real-time agent messages |
| `GET` | `/analyse/{id}/status` | Poll status and retrieve final dashboard spec |
| `POST` | `/analyse/{id}/answer` | Submit user answer to a waiting agent (collaborative mode) |
| `POST` | `/analyse/{id}/hint` | Send a free-text preference hint to influence analysis |
| `GET` | `/download/{id}/{name}` | Download a generated CSV (e.g. cleaned data, RFM table) |

### Start analysis

```json
POST /analyse
{
  "file_path": "storage/uploads/<uuid>_filename.csv",
  "mode": "autonomous"
}
```

`mode` is `"collaborative"` (default) or `"autonomous"`.

### Submit a hint

Hints are injected at two safe points in the pipeline (Strategist planning and Architect layout design) and are never written into agent memory.

```json
POST /analyse/{session_id}/hint
{
  "text": "Focus on geographic breakdown and highlight the UK market"
}
```

---

## Project structure

```
AI-BI-Dashboard-Builder/
├── main.py                        # Uvicorn entry point
├── requirements.txt
├── .env.example
│
├── backend/
│   ├── agents/
│   │   ├── base.py                # BaseAgent — memory, ask_user, LLM helpers
│   │   ├── models.py              # Shared data models (Message, DecisionPoint, etc.)
│   │   ├── message_bus.py         # Async pub/sub + pause/resume for collaborative mode
│   │   ├── orchestrator.py        # Pipeline runner + session state
│   │   ├── cleaner_agent.py       # Data quality and cleaning
│   │   ├── strategist_agent.py    # Analysis planning
│   │   ├── data_scientist_agent.py# Code generation + sandbox execution
│   │   ├── quality_agent.py       # Statistical review and gating
│   │   ├── insight_agent.py       # Narrative generation
│   │   ├── architect_agent.py     # Dashboard layout and composition
│   │   └── sandbox.py             # Safe Python code execution
│   │
│   ├── api/
│   │   ├── upload.py              # FastAPI app + /upload
│   │   ├── analyse.py             # /analyse, /download, SSE stream
│   │   ├── auth.py                # JWT authentication
│   │   └── chat.py                # Dashboard chat endpoint
│   │
│   ├── llm/
│   │   └── client.py              # Task-routed LLM client with fallback chains
│   │
│   ├── parser/                    # Excel + CSV parsing
│   ├── profiler/                  # Column type detection and statistics
│   ├── charts/                    # Chart spec generation helpers
│   ├── dashboard/                 # Dashboard spec builder
│   └── planner/                   # LLM-based analysis planner
│
├── frontend/
│   └── src/
│       ├── pages/                 # Upload, Analysis, Dashboard, Login
│       ├── components/            # AgentProgressFeed, ChartCard, KPICard, etc.
│       └── lib/                   # API client, auth helpers
│
└── storage/
    ├── uploads/                   # Uploaded files
    ├── outputs/                   # Generated dashboard specs
    └── sessions/                  # Per-session CSVs and specs
```

---

## Development notes

**Adding a new analysis pattern**

1. Add the pattern name to `StrategistAgent._fallback_tasks` with its required columns.
2. Add a return format template in `DataScientistAgent._get_return_template`.
3. Add an inspection rule in `QualityAgent._inspect`.
4. The Architect will automatically pick it up and assign a chart type.

**LLM health check**

```bash
curl http://localhost:8000/health/llm
```

Returns which model is active for each task type and which are in cooldown.

**Checking agent logs**

The SSE stream at `/analyse/{id}/events` emits every agent log, decision, error, and user question in real time. The frontend `AgentProgressFeed` component consumes this stream.
