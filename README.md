# Internship Posting Aggregator

A Python service that pulls internship postings from public job-board APIs
(Greenhouse, Lever, Ashby), stores them in PostgreSQL, scores them against my
skills, and serves them through a FastAPI REST API.

**Status:** Stage 1 (ingest) in progress.

## Stack
Python 3.12 · PostgreSQL 16 · SQLAlchemy 2 · Alembic · httpx · pytest · Docker Compose

## Setup (Windows, PowerShell)
```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Data sources
Only public, documented job-board APIs. No HTML scraping, no logins, requests are
sequential with a delay between companies.
