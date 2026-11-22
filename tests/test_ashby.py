import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
import respx

from app.fetchers import ashby
from app.filters import is_internship

FIXTURE = Path(__file__).parent / "fixtures" / "ashby_sample.json"
SWE_INTERN_ID = "84dfad5c-d790-4c4a-9411-40b676b1abbb"


@pytest.fixture
def sample() -> dict:
    return json.loads(FIXTURE.read_text())


def test_parse_maps_fields(sample):
    postings = ashby.parse(sample, company="Veeda AI")
    assert len(postings) == 4

    p = next(p for p in postings if p.source_job_id == SWE_INTERN_ID)
    assert p.source == "ashby"
    assert p.title == "Internship - Software Engineering"
    assert p.location == "Toronto"
    assert p.url == f"https://jobs.ashbyhq.com/veeda-ai/{SWE_INTERN_ID}"
    assert p.posted_at == datetime(2026, 10, 22, 21, 0, 38, 551000, tzinfo=timezone.utc)
    assert p.description_text


def test_hybrid_job_is_not_remote_even_when_isremote_is_true(sample):
    p = next(p for p in ashby.parse(sample, company="Veeda AI") if p.source_job_id == SWE_INTERN_ID)
    assert sample["jobs"][1]["isRemote"] is True   # what Ashby says...
    assert p.remote is False                       # ...but workplaceType is "Hybrid"


def test_remote_workplace_type(sample):
    p = ashby.parse(sample, company="Zip")[3]
    assert p.location == "Remote - West Coast"
    assert p.remote is True


def test_secondary_locations_are_joined(sample):
    p = ashby.parse(sample, company="Veeda AI")[0]  # "Internship", also open outside Toronto
    assert p.location.startswith("Toronto; ")
    assert "Seattle" in p.location


def test_long_location_lists_are_truncated(sample):
    many = [{"location": f"Remote - City {i}"} for i in range(100)]
    job = dict(sample["jobs"][0], secondaryLocations=many)
    p = ashby.parse({"jobs": [job]}, company="Veeda AI")[0]
    assert len(p.location) == ashby.MAX_LOCATION_LEN
    assert p.location.endswith("...")


def test_employment_type_intern_catches_vague_titles(sample):
    job = dict(sample["jobs"][2], employmentType="Intern")  # title has no "intern" in it
    p = ashby.parse({"jobs": [job]}, company="Veeda AI")[0]
    assert is_internship(p.title, p.employment_type)


def test_unlisted_jobs_are_skipped(sample):
    job = dict(sample["jobs"][0], isListed=False)
    assert ashby.parse({"jobs": [job]}, company="Veeda AI") == []


@respx.mock
def test_fetch_calls_board_url(sample):
    route = respx.get("https://api.ashbyhq.com/posting-api/job-board/veeda-ai").mock(
        return_value=httpx.Response(200, json=sample)
    )
    with httpx.Client() as client:
        assert len(ashby.fetch(client, "veeda-ai")["jobs"]) == 4
    assert route.called
