"""Lever Postings API (public, no auth).
Docs: https://github.com/lever/postings-api
"""
from datetime import datetime, timezone

import httpx

from app.fetchers.html_text import html_to_text
from app.filters import is_remote
from app.schemas import NormalizedPosting

SOURCE = "lever"
URL = "https://api.lever.co/v0/postings/{token}"


def fetch(client: httpx.Client, token: str) -> list[dict]:
    """HTTP only. Lever returns a JSON array of postings (Greenhouse wraps its list in {"jobs": [...]})."""
    resp = client.get(URL.format(token=token), params={"mode": "json"})
    resp.raise_for_status()
    return resp.json()


def _description(job: dict) -> str | None:
    """Lever splits a posting into an intro, titled lists (Responsibilities, Requirements...)
    and a closing section. Join them so scoring in Stage 3 sees the whole posting."""
    parts = [job.get("descriptionPlain")]
    for section in job.get("lists", []):
        parts.append(section.get("text"))                  # e.g. "Responsibilities:"
        parts.append(html_to_text(section.get("content")))  # list items arrive as HTML <li>s
    parts.append(job.get("additionalPlain"))
    text = "\n".join(p.strip() for p in parts if p and p.strip())
    return text or None


def parse(data: list[dict], company: str) -> list[NormalizedPosting]:
    postings = []
    for job in data:
        categories = job.get("categories") or {}
        all_locations = categories.get("allLocations") or []
        location = ", ".join(all_locations) or categories.get("location")
        workplace = job.get("workplaceType")  # "remote" | "hybrid" | "onsite" | "unspecified"
        created_ms = job.get("createdAt")
        postings.append(NormalizedPosting(
            source=SOURCE,
            source_job_id=job["id"],             # a UUID string
            company=company,
            title=job["text"].strip(),           # Lever calls the title "text"
            location=location or None,
            url=job["hostedUrl"],
            remote=is_remote(location, None if workplace == "unspecified" else workplace),
            description_text=_description(job),
            # createdAt is milliseconds since 1970-01-01 UTC; fromtimestamp wants seconds
            posted_at=datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc) if created_ms else None,
            employment_type=categories.get("commitment"),  # e.g. "Intern/Co-op"
        ))
    return postings
