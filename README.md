# AI BI Dashboard Builder — Phase 1 MVP

Upload an Excel file → get an interactive BI dashboard automatically.

## Architecture

```
Upload Excel
     │
Excel Parser     (pandas / openpyxl — no AI)
     │
Data Profiler    (pandas — no AI)
     │
Dashboard Planner  ◄── single LLM call (OpenAI)
     │
Chart Generator  (Plotly — no AI)
     │
Dashboard JSON
     │
React Frontend
```

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| Gemini API key | free at [aistudio.google.com](https://aistudio.google.com/app/apikey) |

---

## Backend Setup

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 4. Start the API server
uvicorn main:app --reload --port 8000
```

API is now running at **http://localhost:8000**

- `GET  /health` — health check
- `POST /upload` — upload Excel file, returns dashboard JSON

Interactive docs: **http://localhost:8000/docs**

---

## Frontend Setup

```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Start the dev server
npm run dev
```

App is now running at **http://localhost:3000**

---

## Usage

1. Open **http://localhost:3000**
2. Drag & drop (or click to browse) your Excel file
3. Wait a few seconds while the AI analyses the data
4. Your interactive dashboard appears — KPI cards + charts + data profile

---

## Project Structure

```
AI-BI-Dashboard-Builder/
├── backend/
│   ├── parser/          excel_parser.py      — reads Excel into DataFrames
│   ├── profiler/        profile.py           — column stats (types, nulls, min/max)
│   ├── planner/         llm_planner.py       — one LLM call → KPI + chart plan
│   ├── charts/          chart_generator.py   — plan → Plotly JSON
│   ├── dashboard/       dashboard_builder.py — orchestrates the pipeline
│   └── api/             upload.py            — FastAPI endpoints
├── frontend/
│   └── src/
│       ├── pages/       UploadPage, DashboardPage
│       └── components/  KPICard, ChartCard, ProfileTable
├── storage/
│   ├── uploads/         saved Excel files
│   └── outputs/         saved dashboard JSONs
├── main.py              uvicorn entry point
├── requirements.txt
└── .env.example
```

---

## Roadmap

| Phase | Feature |
|-------|---------|
| ✅ 1 | Upload → parse → profile → LLM plan → charts → dashboard |
| 2 | Planner Agent (multi-step reasoning) |
| 3 | Data Cleaning Agent |
| 4 | Business Understanding Agent |
| 5 | KPI Agent |
| 6 | Visualization Agent |
| 7 | Insight Agent (natural language summaries) |
| 8 | Layout Agent |
| 9 | Chat with Dashboard |
| 10 | Memory (preferences, history) |
| 11 | RAG (business glossary, KPI definitions) |
| 12 | Multi-Agent Supervisor |
