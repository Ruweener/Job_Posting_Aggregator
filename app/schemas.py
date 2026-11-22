"""The common shape every fetcher converts its board's JSON into."""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)  # frozen: fields can't be changed after creation
class NormalizedPosting:
    source: str                 # "greenhouse" | "lever" | "ashby"
    source_job_id: str
    company: str
    title: str
    location: str | None
    url: str
    remote: bool
    description_text: str | None
    posted_at: datetime | None
    # Extra hint from boards that label job types (Lever "Intern/Co-op",
    # Ashby "Intern"). Used by is_internship(); not stored in the database.
    employment_type: str | None = None
