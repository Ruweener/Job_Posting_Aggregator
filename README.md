# Internship Posting Aggregator

A Python service that pulls internship postings from public job-board APIs
(Greenhouse, Lever, Ashby), stores them in PostgreSQL, and (in later stages)
scores them against my skills and serves them through a FastAPI REST API.

**Status:** Stage 1 (ingest) complete. Next: Stage 2 (FastAPI + SQL queries).

## Stack
Python 3.12 · PostgreSQL 16 · SQLAlchemy 2 · Alembic · httpx · pytest · respx · Docker Compose

## How it works

```
companies.yaml ──> fetch() ──> parse() ──> NormalizedPosting ──> is_internship? ──> upsert into Postgres
  (which boards)   (HTTP only)  (pure, per board)  (one shape)        (filters.py)       (ON CONFLICT)
                                                                                     └─> close postings no longer listed
```

- **One fetcher per board** (`app/fetchers/greenhouse.py`, `lever.py`, `ashby.py`). Each has a
  `fetch()` that only does HTTP and a pure `parse()` that turns that board's JSON into the common
  `NormalizedPosting` shape. Adding a board means one new module and one line in `FETCHERS`.
- **Only internships are stored**: the title (or the board's own job-type label) must say
  intern, internship, co-op or student.
- **Idempotent upserts:** `INSERT ... ON CONFLICT (source, source_job_id) DO UPDATE`, so running
  ingest again refreshes rows instead of duplicating them. `first_seen_at` is kept; `last_seen_at` moves.
- **Closing postings:** after a company's board is fetched successfully, its postings that are no
  longer listed get `is_open = false`. A failed fetch skips the company, so an outage never closes
  everything.
- **Term detection:** `Winter 2027` / `Summer 2027` / etc. from the title, falling back to the
  description, skipping graduation dates ("graduating in spring 2028").
- **Polite to APIs:** sequential requests, 1 s between companies, 20 s timeout, no scraping or logins.

## Setup (Windows, PowerShell)

Requires Python 3.12 and Docker Desktop.

```powershell
# 1. Python environment
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Settings: copy the template, then change the password in BOTH lines
copy .env.example .env

# 3. Start Postgres (host port 5433) and create the tables
docker compose up -d --wait
alembic upgrade head
python -m app.check_db
```

## Run

```powershell
python -m app.ingest      # fetch all boards in companies.yaml and upsert internships
pytest                    # run the test suite (offline: uses saved JSON in tests/fixtures)
```

Look at the data:

```powershell
docker exec -it jobagg-db psql -U jobagg -d jobagg
```
```sql
SELECT company, title, location, term FROM postings WHERE is_open ORDER BY first_seen_at DESC;
```

## Adding a company

Find the board token in the company's careers URL (`boards.greenhouse.io/<token>`,
`jobs.lever.co/<token>`, `jobs.ashbyhq.com/<token>`), then add a line to `companies.yaml`:

```yaml
- { name: Example Co, source: greenhouse, token: exampleco }
```

## Project layout

```
app/
  config.py         settings from environment / .env
  db.py             SQLAlchemy engine and session
  models.py         Posting table
  schemas.py        NormalizedPosting (common shape for all boards)
  filters.py        is_internship, detect_term, is_remote
  fetchers/         greenhouse.py, lever.py, ashby.py, html_text.py
  ingest.py         python -m app.ingest
alembic/            database migrations
tests/              pytest suite + fixtures/ (trimmed real API responses)
companies.yaml      which boards to ingest
```

## Roadmap

1. ~~Ingest from Greenhouse, Lever, Ashby into Postgres~~
2. FastAPI: `GET /postings` (filters + pagination), `GET /postings/{id}`, `GET /stats`; indexes
3. Fit scoring + API and database tests
4. GitHub Actions: tests on every push, scheduled daily ingest
5. Deploy to AWS (RDS + EC2/Lambda)
6. Optional React front end

## Data sources

Only public, documented job-board APIs:
[Greenhouse Job Board API](https://developers.greenhouse.io/job-board.html),
[Lever Postings API](https://github.com/lever/postings-api),
[Ashby Job Posting API](https://developers.ashbyhq.com/docs/public-job-posting-api).
