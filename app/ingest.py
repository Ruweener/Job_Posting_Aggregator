"""Daily ingest: fetch every company's board, keep internships, upsert into Postgres.

Run with:  python -m app.ingest
"""
import logging
import time
from pathlib import Path

import httpx
import yaml
from sqlalchemy import func, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.fetchers import ashby, greenhouse, lever
from app.filters import detect_term, is_internship
from app.models import Posting
from app.schemas import NormalizedPosting
from app.scoring import coop_required, in_target_area, score

log = logging.getLogger("ingest")

COMPANIES_FILE = Path(__file__).resolve().parent.parent / "companies.yaml"

# source name -> module with fetch() and parse(). Adding a board = one module + one entry here.
FETCHERS = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby}

DELAY_BETWEEN_COMPANIES = 1.0  # seconds; be polite to the public APIs
USER_AGENT = "internship-posting-aggregator/0.1 (personal project)"


def load_companies(path: Path = COMPANIES_FILE) -> list[dict]:
    data = yaml.safe_load(path.read_text())  # safe_load never runs code embedded in YAML
    return [c for c in data["companies"] if c.get("active", True)]


def to_row(p: NormalizedPosting) -> dict:
    """NormalizedPosting -> dict of column values for the postings table."""
    fit_score, matched_skills = score(p.title, p.description_text)
    return {
        "source": p.source,
        "source_job_id": p.source_job_id,
        "company": p.company,
        "title": p.title,
        "location": p.location,
        "url": p.url,
        "remote": p.remote,
        "description_text": p.description_text,
        "term": detect_term(p.title, p.description_text),
        "posted_at": p.posted_at,
        "is_open": True,
        "fit_score": fit_score,
        "matched_skills": matched_skills,
        "coop_required": coop_required(p.description_text),
        "in_target_area": in_target_area(p.location, p.remote),
    }


def upsert_postings(session: Session, rows: list[dict]) -> None:
    """INSERT ... ON CONFLICT (source, source_job_id) DO UPDATE.
    New jobs are inserted; jobs already in the table get their fields refreshed,
    including scores (so a skills.yaml change applies on the next run).
    first_seen_at is never overwritten."""
    if not rows:
        return
    stmt = insert(Posting).values(rows)
    # "excluded" is Postgres's name for the row we tried to insert
    updatable = ["company", "title", "location", "url", "remote", "description_text", "term", "posted_at",
                 "fit_score", "matched_skills", "coop_required", "in_target_area"]
    stmt = stmt.on_conflict_do_update(
        constraint="uq_postings_source_job",
        set_={**{col: stmt.excluded[col] for col in updatable},
              "is_open": True,              # a job that reappears is open again
              "last_seen_at": func.now()},
    )
    session.execute(stmt)


def close_missing(session: Session, source: str, company: str, seen_ids: set[str]) -> int:
    """Mark this company's open postings that weren't in today's fetch as closed.
    Only called after a successful fetch, so a network error never closes everything."""
    result = session.execute(
        update(Posting)
        .where(Posting.source == source,
               Posting.company == company,
               Posting.is_open.is_(True),
               Posting.source_job_id.not_in(seen_ids))
        .values(is_open=False)
    )
    return result.rowcount


def ingest_company(session: Session, client: httpx.Client, company: dict) -> None:
    name, source, token = company["name"], company["source"], company["token"]
    fetcher = FETCHERS.get(source)
    if fetcher is None:
        log.warning("%s: no fetcher for source %r yet, skipping", name, source)
        return

    try:
        raw = fetcher.fetch(client, token)
    except httpx.HTTPError as exc:
        log.error("%s: fetch failed (%s), skipping; existing postings left as they are", name, exc)
        return

    postings = [p for p in fetcher.parse(raw, company=name) if is_internship(p.title, p.employment_type)]
    # Keyed by job ID: a board listing the same ID twice would make ON CONFLICT fail
    rows = list({p.source_job_id: to_row(p) for p in postings}.values())

    upsert_postings(session, rows)
    closed = close_missing(session, source, name, {r["source_job_id"] for r in rows})
    session.commit()  # one transaction per company: all of it is saved, or none of it
    log.info("%s: %d internships upserted, %d closed", name, len(rows), closed)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    companies = load_companies()
    with httpx.Client(timeout=20.0, headers={"User-Agent": USER_AGENT}) as client, SessionLocal() as session:
        for i, company in enumerate(companies):
            if i:
                time.sleep(DELAY_BETWEEN_COMPANIES)
            ingest_company(session, client, company)


if __name__ == "__main__":  # runs only via `python -m app.ingest`, not on import
    main()
