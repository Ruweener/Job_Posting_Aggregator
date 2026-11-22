"""Unit tests for the database-free parts of ingest.
Upserts and closing are tested against Postgres in test_db_ingest.py."""
import contextlib
from datetime import datetime, timezone

import app.ingest as ingest
from app.ingest import load_companies, to_row
from app.schemas import NormalizedPosting


def test_load_companies_skips_inactive(tmp_path):  # tmp_path: a temp folder pytest provides
    f = tmp_path / "companies.yaml"
    f.write_text(
        "companies:\n"
        "  - { name: A, source: greenhouse, token: a }\n"
        "  - { name: B, source: lever, token: b, active: false }\n"
    )
    assert [c["name"] for c in load_companies(f)] == ["A"]


def test_real_companies_file_is_valid():
    for c in load_companies():
        assert {"name", "source", "token"} <= c.keys()
        assert c["source"] in {"greenhouse", "lever", "ashby"}


def test_to_row_fills_term_and_opens_posting():
    p = NormalizedPosting(
        source="greenhouse", source_job_id="1", company="Stripe",
        title="Software Engineering Intern (Winter 2027)", location="Toronto",
        url="https://example.com", remote=False, description_text=None,
        posted_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    row = to_row(p)
    assert row["term"] == "Winter 2027"
    assert row["is_open"] is True
    assert "employment_type" not in row  # a hint for filtering, not a column


def test_main_exits_1_when_every_company_fails(monkeypatch):
    # monkeypatch swaps attributes for this test only and puts them back afterwards.
    # nullcontext() stands in for a database session, so no database is needed.
    monkeypatch.setattr(ingest, "load_companies", lambda: [{"name": "A", "source": "greenhouse", "token": "a"}])
    monkeypatch.setattr(ingest, "ingest_company", lambda session, client, company: False)
    monkeypatch.setattr(ingest, "SessionLocal", contextlib.nullcontext)
    assert ingest.main() == 1
