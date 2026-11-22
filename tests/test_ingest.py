"""Unit tests for the database-free parts of ingest. The upsert itself is checked
by running ingest twice against Postgres (see README); DB tests come in Stage 3."""
from datetime import datetime, timezone

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
