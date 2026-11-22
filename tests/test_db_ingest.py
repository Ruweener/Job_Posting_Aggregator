"""Ingest against a real Postgres test database: upsert, duplicates, closing, failures."""
import json
from pathlib import Path

import httpx
import respx
from sqlalchemy import func, select

from app.ingest import close_missing, ingest_company, upsert_postings
from app.models import Posting

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "greenhouse_sample.json").read_text())
BOARD_URL = "https://boards-api.greenhouse.io/v1/boards/stripe/jobs"
STRIPE = {"name": "Stripe", "source": "greenhouse", "token": "stripe"}


def row(job_id: str, company: str = "Stripe", **overrides) -> dict:
    base = {"source": "greenhouse", "source_job_id": job_id, "company": company,
            "title": f"Intern {job_id}", "location": "Toronto", "url": "https://example.com",
            "remote": False, "description_text": None, "term": "Unknown", "posted_at": None,
            "is_open": True, "fit_score": 0, "matched_skills": [], "coop_required": False,
            "in_target_area": True}
    return base | overrides  # | merges dicts; the right side wins


def count(session) -> int:
    return session.scalar(select(func.count()).select_from(Posting))


def get(session, job_id: str) -> Posting:
    return session.scalars(select(Posting).where(Posting.source_job_id == job_id)).one()


def test_upsert_twice_creates_no_duplicates(db_session):
    upsert_postings(db_session, [row("1"), row("2")])
    upsert_postings(db_session, [row("1"), row("2")])
    assert count(db_session) == 2


def test_upsert_updates_fields_but_keeps_first_seen(db_session):
    upsert_postings(db_session, [row("1", title="Old title")])
    first_seen = get(db_session, "1").first_seen_at

    upsert_postings(db_session, [row("1", title="New title", fit_score=7)])
    db_session.expire_all()  # forget cached objects so the next read hits the database
    p = get(db_session, "1")
    assert (p.title, p.fit_score) == ("New title", 7)
    assert p.first_seen_at == first_seen


def test_close_missing_only_closes_that_companys_missing_postings(db_session):
    upsert_postings(db_session, [row("1"), row("2"), row("3", company="Other")])
    closed = close_missing(db_session, "greenhouse", "Stripe", seen_ids={"1"})
    db_session.expire_all()
    assert closed == 1
    assert get(db_session, "1").is_open is True
    assert get(db_session, "2").is_open is False   # Stripe, not seen: closed
    assert get(db_session, "3").is_open is True    # other company: untouched


def test_reappearing_posting_is_reopened(db_session):
    upsert_postings(db_session, [row("1")])
    close_missing(db_session, "greenhouse", "Stripe", seen_ids=set())
    upsert_postings(db_session, [row("1")])
    db_session.expire_all()
    assert get(db_session, "1").is_open is True


@respx.mock
def test_ingest_company_end_to_end(db_session):
    """Mocked HTTP -> real parse -> internship filter -> real upsert, run twice."""
    respx.get(BOARD_URL).mock(return_value=httpx.Response(200, json=FIXTURE))
    with httpx.Client() as client:
        ingest_company(db_session, client, STRIPE)
        ingest_company(db_session, client, STRIPE)

    # The fixture has 3 jobs; "Abuse Investigator" is not an internship and is dropped
    titles = set(db_session.scalars(select(Posting.title)))
    assert titles == {"High School Internship, Software Engineering (Summer 2027)", "Data Analyst, Intern"}
    p = get(db_session, "8241260")
    assert p.term == "Summer 2027"
    assert p.fit_score is not None and p.matched_skills is not None


@respx.mock
def test_ingest_closes_posting_that_disappears(db_session):
    route = respx.get(BOARD_URL)
    route.mock(return_value=httpx.Response(200, json=FIXTURE))
    with httpx.Client() as client:
        ingest_company(db_session, client, STRIPE)
        smaller = {"jobs": [j for j in FIXTURE["jobs"] if j["id"] != 8194287]}
        route.mock(return_value=httpx.Response(200, json=smaller))
        ingest_company(db_session, client, STRIPE)

    db_session.expire_all()
    assert get(db_session, "8194287").is_open is False
    assert get(db_session, "8241260").is_open is True


@respx.mock
def test_failed_fetch_leaves_existing_postings_open(db_session):
    upsert_postings(db_session, [row("8194287")])
    respx.get(BOARD_URL).mock(return_value=httpx.Response(503))
    with httpx.Client() as client:
        ingest_company(db_session, client, STRIPE)  # must not raise
    db_session.expire_all()
    assert get(db_session, "8194287").is_open is True
