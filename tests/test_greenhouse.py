import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
import respx

from app.fetchers import greenhouse

FIXTURE = Path(__file__).parent / "fixtures" / "greenhouse_sample.json"


@pytest.fixture  # a fixture is setup code pytest runs and passes into any test that names it
def sample() -> dict:
    return json.loads(FIXTURE.read_text())


def test_parse_maps_fields(sample):
    postings = greenhouse.parse(sample, company="Stripe")
    assert len(postings) == 3

    p = next(p for p in postings if p.source_job_id == "8194287")
    assert p.source == "greenhouse"
    assert p.company == "Stripe"
    assert p.title == "Data Analyst, Intern"
    assert p.location == "Toronto"
    assert p.url.startswith("https://")
    assert p.remote is False
    # 11:05:36 at -04:00 is 15:05:36 UTC: timezone offsets are kept, not dropped
    assert p.posted_at == datetime(2026, 10, 1, 15, 5, 36, tzinfo=timezone.utc)


def test_parse_strips_html(sample):
    p = greenhouse.parse(sample, company="Stripe")[0]
    assert p.description_text
    assert "<" not in p.description_text and "&lt;" not in p.description_text
    assert "high school students" in p.description_text


@respx.mock  # intercepts httpx calls, so no real network request is made
def test_fetch_calls_board_url(sample):
    route = respx.get("https://boards-api.greenhouse.io/v1/boards/stripe/jobs").mock(
        return_value=httpx.Response(200, json=sample)
    )
    with httpx.Client() as client:
        data = greenhouse.fetch(client, "stripe")
    assert route.called
    assert route.calls.last.request.url.params["content"] == "true"
    assert len(data["jobs"]) == 3


@respx.mock
def test_fetch_raises_on_unknown_board():
    respx.get("https://boards-api.greenhouse.io/v1/boards/nope/jobs").mock(return_value=httpx.Response(404))
    with httpx.Client() as client, pytest.raises(httpx.HTTPStatusError):
        greenhouse.fetch(client, "nope")
