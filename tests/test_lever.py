import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
import respx

from app.fetchers import lever
from app.filters import is_internship

FIXTURE = Path(__file__).parent / "fixtures" / "lever_sample.json"
INTERN_ID = "5514238a-8301-49f1-8116-26d38ea0900c"


@pytest.fixture
def sample() -> list[dict]:
    return json.loads(FIXTURE.read_text())


def test_parse_maps_fields(sample):
    postings = lever.parse(sample, company="Kepler Communications")
    assert len(postings) == 2

    p = next(p for p in postings if p.source_job_id == INTERN_ID)
    assert p.source == "lever"
    assert p.title == "Software Engineering Intern (January 2027)"
    assert p.location == "Toronto, Ontario"
    assert p.url == f"https://jobs.lever.co/kepler/{INTERN_ID}"
    assert p.remote is False                 # workplaceType "hybrid"
    assert p.employment_type == "Intern/Co-op"
    assert p.posted_at == datetime.fromtimestamp(1792163729.033, tz=timezone.utc)
    assert p.posted_at.year == 2026


def test_description_includes_list_sections(sample):
    p = next(p for p in lever.parse(sample, company="Kepler") if p.source_job_id == INTERN_ID)
    assert "Responsibilities:" in p.description_text
    assert "<li>" not in p.description_text


def test_commitment_identifies_internships(sample):
    postings = lever.parse(sample, company="Kepler")
    assert [is_internship(p.title, p.employment_type) for p in postings] == [True, False]


def test_remote_from_workplace_type(sample):
    job = dict(sample[1], workplaceType="remote")
    assert lever.parse([job], company="Kepler")[0].remote is True


@respx.mock
def test_fetch_requests_json_mode(sample):
    route = respx.get("https://api.lever.co/v0/postings/kepler").mock(
        return_value=httpx.Response(200, json=sample)
    )
    with httpx.Client() as client:
        assert len(lever.fetch(client, "kepler")) == 2
    assert route.calls.last.request.url.params["mode"] == "json"
