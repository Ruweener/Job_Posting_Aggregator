"""Greenhouse Job Board API (public, no auth).
Docs: https://developers.greenhouse.io/job-board.html
"""
from datetime import datetime

import httpx

from app.fetchers.html_text import html_to_text
from app.filters import is_remote
from app.schemas import NormalizedPosting

SOURCE = "greenhouse"
URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


def fetch(client: httpx.Client, token: str) -> dict:
    """HTTP only: return the board's raw JSON. Raises on 4xx/5xx so ingest can skip the company."""
    resp = client.get(URL.format(token=token), params={"content": "true"})  # content=true includes descriptions
    resp.raise_for_status()
    return resp.json()


def parse(data: dict, company: str) -> list[NormalizedPosting]:
    """Pure function: raw JSON in, NormalizedPosting list out. Tested with saved JSON."""
    postings = []
    for job in data["jobs"]:
        location = (job.get("location") or {}).get("name")
        published = job.get("first_published") or job.get("updated_at")
        postings.append(NormalizedPosting(
            source=SOURCE,
            source_job_id=str(job["id"]),        # numeric on Greenhouse; stored as text for all sources
            company=company,
            title=job["title"].strip(),
            location=location.strip() if location else None,
            url=job["absolute_url"],
            remote=is_remote(location),           # Greenhouse has no structured remote field
            description_text=html_to_text(job.get("content")),
            posted_at=datetime.fromisoformat(published) if published else None,
        ))
    return postings
