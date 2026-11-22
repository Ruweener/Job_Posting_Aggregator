"""Ashby public Job Posting API (no auth).
Docs: https://developers.ashbyhq.com/docs/public-job-posting-api
"""
from datetime import datetime

import httpx

from app.fetchers.html_text import html_to_text
from app.filters import is_remote
from app.schemas import NormalizedPosting

SOURCE = "ashby"
URL = "https://api.ashbyhq.com/posting-api/job-board/{token}"
MAX_LOCATION_LEN = 500  # matches the postings.location column size


def fetch(client: httpx.Client, token: str) -> dict:
    """HTTP only. Returns {"apiVersion": ..., "jobs": [...]}."""
    resp = client.get(URL.format(token=token), params={"includeCompensation": "true"})
    resp.raise_for_status()
    return resp.json()


def _location(job: dict) -> str | None:
    """Primary location plus any secondary ones, e.g. "Toronto; Remote - Canada".
    Secondary locations matter: a job listed as "San Francisco" may also be open in Toronto."""
    names = [job.get("location")] + [s.get("location") for s in job.get("secondaryLocations") or []]
    unique = list(dict.fromkeys(n.strip() for n in names if n and n.strip()))  # dedupe, keep order
    text = "; ".join(unique)
    if len(text) > MAX_LOCATION_LEN:
        text = text[: MAX_LOCATION_LEN - 3] + "..."
    return text or None


def parse(data: dict, company: str) -> list[NormalizedPosting]:
    postings = []
    for job in data["jobs"]:
        if job.get("isListed") is False:  # unlisted jobs aren't meant to be public
            continue
        location = _location(job)
        published = job.get("publishedAt")
        postings.append(NormalizedPosting(
            source=SOURCE,
            source_job_id=job["id"],
            company=company,
            title=job["title"].strip(),
            location=location,
            url=job["jobUrl"],
            # Not job["isRemote"]: in Step 0 it was True for a Toronto *hybrid* internship.
            # workplaceType ("Remote" | "Hybrid" | "OnSite" | None) was accurate.
            remote=is_remote(location, job.get("workplaceType")),
            description_text=job.get("descriptionPlain") or html_to_text(job.get("descriptionHtml")),
            posted_at=datetime.fromisoformat(published) if published else None,
            employment_type=job.get("employmentType"),  # "FullTime" | "Intern" | ...
        ))
    return postings
