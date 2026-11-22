"""API endpoints against the test database, through FastAPI's TestClient."""
from datetime import datetime, timedelta, timezone

import pytest

from app.models import Posting

NOW = datetime.now(timezone.utc)


@pytest.fixture
def seeded(db_session):
    """Five postings chosen to exercise each filter, returned by a short name."""
    postings = {
        "kepler": Posting(source="lever", source_job_id="k1", company="Kepler", title="Software Engineering Intern",
                          location="Toronto, Ontario", url="https://x/k1", remote=False, term="Winter 2027",
                          description_text="Python and SQL", posted_at=NOW - timedelta(days=1),
                          fit_score=7, matched_skills=["Python", "SQL"], in_target_area=True, is_open=True),
        "stripe": Posting(source="greenhouse", source_job_id="s1", company="Stripe", title="Data Analyst, Intern",
                          location="San Francisco", url="https://x/s1", remote=False, term="Summer 2027",
                          description_text="SQL dashboards", posted_at=NOW - timedelta(days=3),
                          fit_score=3, matched_skills=["SQL"], in_target_area=False, is_open=True),
        "remote": Posting(source="ashby", source_job_id="r1", company="Cohere", title="ML Intern",
                          location="Remote - Canada", url="https://x/r1", remote=True, term="Winter 2027",
                          description_text="Research with 100% focus", posted_at=NOW - timedelta(days=10),
                          fit_score=10, matched_skills=["Python"], in_target_area=True, is_open=True),
        "coop": Posting(source="greenhouse", source_job_id="d1", company="Databricks", title="SWE Co-op",
                        location="Toronto", url="https://x/d1", remote=False, term="Summer 2027",
                        description_text="enrolled in a co-op program", posted_at=None,
                        fit_score=5, matched_skills=["Java"], coop_required=True, in_target_area=True,
                        is_open=True),
        "closed": Posting(source="greenhouse", source_job_id="c1", company="Stripe", title="Old Intern",
                          location="Toronto", url="https://x/c1", remote=False, term="Winter 2027",
                          posted_at=NOW - timedelta(days=40), fit_score=9, in_target_area=True, is_open=False),
    }
    db_session.add_all(postings.values())
    db_session.flush()  # sends the INSERTs so ids are assigned, without committing
    return postings


def titles(resp) -> list[str]:
    assert resp.status_code == 200, resp.text
    return [p["title"] for p in resp.json()["items"]]


def test_list_defaults_to_open_postings_newest_first(client, seeded):
    resp = client.get("/postings")
    assert resp.json()["total"] == 4
    # Newest first; the co-op posting has no date, so it goes last
    assert titles(resp) == ["Software Engineering Intern", "Data Analyst, Intern", "ML Intern", "SWE Co-op"]
    assert "description_text" not in resp.json()["items"][0]  # the list view leaves it out


def test_include_closed(client, seeded):
    assert client.get("/postings?include_closed=true").json()["total"] == 5


@pytest.mark.parametrize("query, expected", [
    ("term=Winter 2027", {"Software Engineering Intern", "ML Intern"}),
    ("location=TORONTO", {"Software Engineering Intern", "SWE Co-op"}),   # case-insensitive
    ("remote=true", {"ML Intern"}),
    ("company=Stripe", {"Data Analyst, Intern"}),
    ("q=dashboards", {"Data Analyst, Intern"}),                            # matches the description
    ("q=100%25", {"ML Intern"}),                                           # %25 is "%": literal, not a wildcard
    ("min_score=7", {"Software Engineering Intern", "ML Intern"}),
    ("in_target_area=true", {"Software Engineering Intern", "ML Intern", "SWE Co-op"}),
    ("in_target_area=true&hide_coop_required=true", {"Software Engineering Intern", "ML Intern"}),
    ("term=Fall 2030", set()),
])
def test_filters(client, seeded, query, expected):
    assert set(titles(client.get(f"/postings?{query}"))) == expected


def test_sort_by_score(client, seeded):
    assert titles(client.get("/postings?sort=score"))[:2] == ["ML Intern", "Software Engineering Intern"]


def test_pagination(client, seeded):
    page1 = client.get("/postings?limit=2&offset=0").json()
    page2 = client.get("/postings?limit=2&offset=2").json()
    assert page1["total"] == page2["total"] == 4
    ids = [p["id"] for p in page1["items"] + page2["items"]]
    assert len(ids) == len(set(ids)) == 4  # no overlap between pages, nothing missing


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "min_score=11", "q=a", "sort=random"])
def test_invalid_parameters_return_422(client, query):
    assert client.get(f"/postings?{query}").status_code == 422


def test_get_posting_detail(client, seeded):
    resp = client.get(f"/postings/{seeded['kepler'].id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Software Engineering Intern"
    assert body["description_text"] == "Python and SQL"
    assert body["matched_skills"] == ["Python", "SQL"]


def test_get_posting_404(client):
    resp = client.get("/postings/999999")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Posting not found"}


def test_stats(client, seeded):
    body = client.get("/stats").json()
    assert (body["total"], body["open"]) == (5, 4)
    by_company = {c["company"]: (c["total"], c["open"]) for c in body["by_company"]}
    assert by_company["Stripe"] == (2, 1)
    assert {t["term"]: t["open"] for t in body["by_term"]} == {"Winter 2027": 2, "Summer 2027": 2}
    assert sum(w["posted"] for w in body["by_week"]) == 5  # all within the default 12 weeks


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
