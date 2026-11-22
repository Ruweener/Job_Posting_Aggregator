"""Pydantic response models: the exact JSON shape the API promises to return.
FastAPI validates every response against these and uses them to build /docs."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PostingSummary(BaseModel):
    """One row in a list. Leaves out the long description to keep list responses small."""
    # from_attributes lets Pydantic read fields straight off a SQLAlchemy Posting object
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    company: str
    title: str
    location: str | None
    url: str
    remote: bool
    term: str
    posted_at: datetime | None
    first_seen_at: datetime
    last_seen_at: datetime
    is_open: bool
    fit_score: int | None
    matched_skills: list[str] | None
    coop_required: bool
    in_target_area: bool


class PostingDetail(PostingSummary):
    """A single posting, including its full description."""
    source_job_id: str
    description_text: str | None


class PostingPage(BaseModel):
    """A page of results. total is the count across all pages, so a client can build pagination."""
    total: int
    limit: int
    offset: int
    items: list[PostingSummary]
