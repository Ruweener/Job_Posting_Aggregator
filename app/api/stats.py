"""GET /stats: aggregate counts, written as plain SQL so every GROUP BY is visible."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db

router = APIRouter(tags=["stats"])


class CompanyCount(BaseModel):
    company: str
    total: int
    open: int


class WeekCount(BaseModel):
    week_start: str  # Monday of that week, YYYY-MM-DD
    posted: int


class TermCount(BaseModel):
    term: str
    open: int


class Stats(BaseModel):
    total: int
    open: int
    by_company: list[CompanyCount]
    by_week: list[WeekCount]
    by_term: list[TermCount]


# COUNT(*) FILTER (WHERE ...) is Postgres's way to count a subset inside one GROUP BY,
# instead of running a second query or a CASE expression.
BY_COMPANY_SQL = text("""
    SELECT company,
           COUNT(*)                          AS total,
           COUNT(*) FILTER (WHERE is_open)   AS open
    FROM postings
    GROUP BY company
    ORDER BY open DESC, company
""")

# date_trunc('week', ...) rounds a timestamp down to Monday 00:00, so all postings from the
# same week fall into one group. posted_at is when the company published the job; if a
# board didn't give one, first_seen_at (when we first ingested it) is the fallback.
BY_WEEK_SQL = text("""
    SELECT to_char(date_trunc('week', COALESCE(posted_at, first_seen_at)), 'YYYY-MM-DD') AS week_start,
           COUNT(*) AS posted
    FROM postings
    WHERE COALESCE(posted_at, first_seen_at) >= now() - make_interval(weeks => :weeks)
    GROUP BY 1
    ORDER BY 1 DESC
""")

BY_TERM_SQL = text("""
    SELECT term, COUNT(*) AS open
    FROM postings
    WHERE is_open
    GROUP BY term
    ORDER BY open DESC
""")

TOTALS_SQL = text("SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE is_open) AS open FROM postings")


@router.get("/stats", response_model=Stats)
def stats(
    db: Annotated[Session, Depends(get_db)],
    weeks: Annotated[int, Query(ge=1, le=104, description="How many weeks back by_week covers")] = 12,
) -> Stats:
    """Counts by company, by week posted (last `weeks` weeks) and by term."""
    totals = db.execute(TOTALS_SQL).one()
    # .mappings() returns each row as a dict-like {column: value}, which Pydantic can read
    return Stats(
        total=totals.total,
        open=totals.open,
        by_company=db.execute(BY_COMPANY_SQL).mappings().all(),
        # :weeks is a bound parameter: the value is sent separately from the SQL text
        by_week=db.execute(BY_WEEK_SQL, {"weeks": weeks}).mappings().all(),
        by_term=db.execute(BY_TERM_SQL).mappings().all(),
    )
