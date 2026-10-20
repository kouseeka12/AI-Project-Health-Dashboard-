# Project Health Reporting Agent

## MongoDB backend and web dashboard

The local web app connects the browser to a FastAPI backend and **real MongoDB**:

```text
Browser dashboard -> FastAPI API -> project_health.reports (MongoDB)
                             |
                       Existing Excel RAG analyzer
```

Reports, metrics, recommendations, timestamps, and editable notes are stored as
MongoDB documents. The dashboard does not use localStorage or a mock database.
The existing command-line AI workflow remains unchanged. The web dashboard
uses deterministic analysis and does not call Gemini or require an API key.

### Start the demo on Windows

Use Python 3.10+ and MongoDB Community Server. Install dependencies from the
repository root (a virtual environment is recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If MongoDB is already running as a Windows service, leave it running and skip
the next command. Otherwise, put `mongod.exe` on PATH, or use the local copy
in `.local\mongodb\bin`, and run in **terminal 1**:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_mongodb.ps1
```

In **terminal 2**:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_demo.ps1
```

Open **http://127.0.0.1:8000**. Keep both terminals open. Stop each server with
Ctrl+C; database files remain in `.local\mongodb\data` across restarts.
Never delete that directory if you want to keep your saved reports.

Configuration is through backend environment variables:

```powershell
$env:MONGODB_URI = "mongodb://127.0.0.1:27017"
$env:MONGODB_DATABASE = "project_health"
```

Set these before starting the dashboard. Never put credentials into frontend
code or commit them. This is an unauthenticated **localhost-only teaching demo**,
not a production deployment. Do not expose its ports publicly.

### Demonstrate MongoDB to your professor

1. Show **MongoDB connected**, database `project_health`, collection `reports`,
   and the live document count on the dashboard.
2. Leave the analysis date at **2026-07-09**, which matches the provided sample
   plans. Click **Analyze & save sample plans**. Two fresh reports are inserted.
   Each click deliberately creates new historical report documents.
3. Click **View document** to show the actual MongoDB ObjectId, metrics, RAG
   status, and stored JSON fetched from the API.
4. Enter a note and click **Save notes to MongoDB**. Refresh the browser and
   reopen the document to show that the update persisted.
5. Optionally install **MongoDB Compass**, connect to
   `mongodb://127.0.0.1:27017`, then open **project_health > reports**. Refresh
   Compass after each operation to show the same ObjectId and notes.
6. Stop and restart the API and MongoDB, then refresh the dashboard. Reports
   should still be present: the database, not the browser, stores them.
7. Delete a report and refresh Compass to demonstrate deletion. Deletion is
   permanent and requires confirmation in the dashboard.
8. Optionally upload an `.xlsx` project plan (10 MB maximum). Supported
   workbooks must use the structure recognized by the existing analyzer.

Interactive API documentation is at **http://127.0.0.1:8000/docs**:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Ping MongoDB and count saved documents |
| GET | `/api/reports?page=1` | Read saved reports, 20 per page |
| POST | `/api/reports/samples` | Analyze both supplied workbooks and insert reports |
| POST | `/api/reports/upload` | Analyze and save an uploaded workbook |
| GET | `/api/reports/{id}` | Read a document by its MongoDB ObjectId |
| PATCH | `/api/reports/{id}` | Update notes with `{"notes": "..."}` |
| DELETE | `/api/reports/{id}` | Delete one saved report |

MongoDB connection failures return HTTP **503** and are displayed in the UI;
the app never pretends to save data when the database is unavailable.

### Validate the integration

With MongoDB running:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The integration tests use an isolated, randomly named test database and delete
only that database afterwards. They exercise real MongoDB CRUD, uploads,
pagination, persistence across application connections, and failure responses.
They also compare uploaded report calculations with the existing analyzer.

An AI-powered Project Health Reporting Agent developed for the **Zycus AI Engineer Intern Technical Assignment**.

The solution automatically analyzes Microsoft Excel project plans, determines project health using a configurable **Red–Amber–Green (RAG)** framework, performs AI-assisted reasoning using **Google Gemini 2.5 Flash**, and generates executive-ready project reports along with a portfolio-level monthly synthesis.

---

# Project Overview

Professional Services leadership often spends significant time collecting weekly project updates from Project Managers. This project automates that workflow by combining deterministic project analytics with AI-assisted reasoning.

The system:

* Reads Excel project plans
* Calculates project health using configurable RAG rules
* Identifies delivery risks
* Analyzes stakeholder sentiment
* Generates executive-level recommendations
* Produces weekly reports and portfolio summaries

The architecture intentionally separates **deterministic calculations** from **LLM reasoning**, ensuring that measurable project metrics remain auditable while leveraging AI only where natural language understanding adds value.

---

# Features

* Automated Project Health Reporting
* Configurable RAG Framework
* Google Gemini 2.5 Flash Integration
* Deterministic Project Health Scoring
* Stakeholder Sentiment Analysis
* Delivery Risk Identification
* Portfolio-Level Executive Insights
* Weekly Markdown Reports
* Executive Monthly Portfolio Summary
* Execution Trace Logging
* Robust JSON Extraction
* Retry Logic with Exponential Backoff
* Graceful Deterministic Fallback

---

# Project Structure

```text
project-health-reporting-agent/
│
├── src/
│   ├── project_health_agent.py
│   └── agentic_project_health_agent.py
│
├── methodology/
│   └── RAG_Methodology.md
│
├── sample_outputs/
│   ├── *.md
│   ├── agent_execution_trace.json
│   └── agentic_project_health_summary.json
│
├── executive_monthly_synthesis.pptx
├── prompts.md
├── config.json
├── requirements.txt
└── README.md
```

---

# Solution Architecture

```text
Excel Project Plans
        │
        ▼
Read Excel Files
        │
        ▼
Project Analyzer
        │
        ├──────────────┐
        ▼              ▼
Risk Detector    Stakeholder Sentiment
        │              │
        └──────┬───────┘
               ▼
Executive Portfolio Synthesizer
               ▼
Weekly Reports
               ▼
Portfolio Summary
               ▼
Execution Trace
```

---

# RAG Methodology

Project health is determined using configurable weighted indicators.

| Indicator             | Weight |
| --------------------- | -----: |
| Schedule Health       |    35% |
| Milestone Health      |    20% |
| Active Blockers       |    20% |
| Progress              |    15% |
| Stakeholder Sentiment |     5% |
| Data Quality          |     5% |

The scoring thresholds are configurable through `config.json`.

---

# AI Design

The system follows a **hybrid AI architecture**.

## Deterministic Engine

Responsible for:

* Schedule analysis
* Milestone evaluation
* Progress calculation
* Blocker detection
* Data completeness checks
* Final RAG score

These values are treated as the **single source of truth**.

## Gemini AI

Google Gemini is used only for reasoning tasks including:

* Stakeholder sentiment analysis
* Risk theme identification
* Executive summaries
* Portfolio synthesis
* Action recommendations

This approach minimizes hallucinations while maintaining explainable project health reporting.

---

# Requirements

* Python 3.10 or higher
* Google Gemini API Key

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# Configuration

The application is configured through `config.json`.

Example:

```json
{
  "llm": {
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "temperature": 0.1,
    "max_retries": 3,
    "retry_backoff_seconds": 1.5
  }
}
```

---

## Running the Project

Open a terminal in the project root directory (the folder containing `README.md`, `config.json`, and the sample Excel files).

### Set the Gemini API Key

```powershell
$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```

### Run the Application

```powershell
python .\src\agentic_project_health_agent.py `
".\S2P Project (1).xlsx" `
".\Project Plan B (1).xlsx" `
--as-of 2026-07-09 `
--output-dir sample_outputs `
--config config.json `
--llm-provider gemini
```

---

## Deterministic Mode (Without AI)

```powershell
python .\src\agentic_project_health_agent.py `
".\S2P Project (1).xlsx" `
".\Project Plan B (1).xlsx" `
--as-of 2026-07-09 `
--output-dir sample_outputs `
--config config.json `
--llm-provider none
```

# Generated Outputs

The agent produces:

* Weekly Project Health Reports (Markdown)
* Portfolio Health Summary (JSON)
* Agent Execution Trace (JSON)
* Executive Monthly Presentation (PowerPoint)

---

# Execution Trace

Every execution records:

* Timestamp
* Workflow Node
* Execution Status
* LLM Provider
* Model Used
* Execution Time
* Fallback Information

This provides complete transparency and auditability.

---

# Reliability Features

The implementation includes:

* Robust JSON extraction
* Automatic retry with exponential backoff
* Structured logging
* Missing-data handling
* Graceful deterministic fallback
* Configurable scoring framework

---

# Assumptions

The supplied project plans do not contain:

* Planned Budget
* Actual Budget
* Forecast Budget

Instead of estimating missing financial values, the system explicitly reports a **Budget Visibility Gap** and recommends capturing these fields in future project exports.

---

# Design Decisions

The solution intentionally separates deterministic analytics from AI reasoning.

Project metrics such as schedule health, milestone status, progress, and blockers are computed deterministically to ensure reproducibility and auditability.

Google Gemini is used only for language-intensive tasks such as stakeholder sentiment analysis, executive summaries, portfolio synthesis, and actionable recommendations.

This hybrid architecture provides:

* Reliable project scoring
* Explainable AI outputs
* Reduced hallucination risk
* Enterprise-ready design
* Easy extensibility

---

# Future Improvements

Potential enhancements include:

* Microsoft Teams notifications
* SharePoint integration
* Email report distribution
* Interactive dashboard
* Historical trend analysis
* Budget forecasting
* Resource utilization analytics
* Multi-project portfolio monitoring

---

# Deliverables

* RAG Methodology
* AI Project Health Reporting Agent
* Weekly Project Reports
* Executive Monthly Presentation
* Source Code
* Configuration Files
* Documentation

---

# Author

Prepared as part of the **Zycus AI Engineer Intern Technical Assignment**, demonstrating the application of deterministic analytics and Google Gemini-powered reasoning for automated project health reporting.
