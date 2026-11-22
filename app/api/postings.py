"""GET /postings and GET /postings/{id}."""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.models import PostingDetail, PostingPage
from app.models import Posting

router = APIRouter(prefix="/postings", tags=["postings"])


def _escape_like(value: str) -> str:
    """% and _ are wildcards in LIKE. Escape them so a search for "50%" means a literal 50%."""
    return value.replace("\\", "\\\\").replace("%", "\%").replace("_", "\_")


@router.get("", response_model=PostingPage)
def list_postings(
    db: Annotated[Session, Depends(get_db)],
    # Query(...) declares a query-string parameter, with validation and a description for /docs
    term: Annotated[str | None, Query(description='Exact term, e.g. "Winter 2027"')] = None,
    location: Annotated[str | None, Query(description='Substring of location, e.g. "toronto"')] = None,
    remote: Annotated[bool | None, Query(description="Only remote (true) or only non-remote (false)")] = None,
    company: Annotated[str | None, Query(description="Exact company name")] = None,
    q: Annotated[str | None, Query(min_length=2, description="Keyword in title or description")] = None,
    min_score: Annotated[int | None, Query(ge=0, le=10, description="Minimum fit score (0-10)")] = None,
    in_target_area: Annotated[bool | None, Query(
        description="Ontario or remote-Canada postings only (true), or only outside it (false)")] = None,
    hide_coop_required: Annotated[bool, Query(
        description="Hide postings whose description says a co-op program is required. "
                    "Some offer a non-co-op internship track too, so read before ruling one out.")] = False,
    sort: Annotated[Literal["newest", "score"], Query(
        description="newest = most recently posted first; score = best fit first")] = "newest",
    include_closed: Annotated[bool, Query(description="Also return postings no longer listed")] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PostingPage:
    # Build one list of WHERE conditions, then use it for both the count and the page query
    conditions = []
    if not include_closed:
        conditions.append(Posting.is_open.is_(True))
    if term:
        conditions.append(Posting.term == term)
    if location:
        # ILIKE = case-insensitive LIKE. SQLAlchemy sends the value as a bound parameter,
        # never pasted into the SQL string, so this is safe from SQL injection.
        conditions.append(Posting.location.ilike(f"%{_escape_like(location)}%", escape="\\"))
    if remote is not None:
        conditions.append(Posting.remote.is_(remote))
    if company:
        conditions.append(Posting.company == company)
    if q:
        pattern = f"%{_escape_like(q)}%"
        conditions.append(or_(Posting.title.ilike(pattern, escape="\\"),
                              Posting.description_text.ilike(pattern, escape="\\")))
    if min_score is not None:
        conditions.append(Posting.fit_score >= min_score)
    if in_target_area is not None:
        conditions.append(Posting.in_target_area.is_(in_target_area))
    if hide_coop_required:
        conditions.append(Posting.coop_required.is_(False))

    # Postings without a date or score go last; id breaks ties so pages are stable
    newest = Posting.posted_at.desc().nulls_last()
    order_by = ([Posting.fit_score.desc().nulls_last(), newest] if sort == "score" else [newest])

    total = db.scalar(select(func.count()).select_from(Posting).where(*conditions))
    rows = db.scalars(
        select(Posting)
        .where(*conditions)
        .order_by(*order_by, Posting.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return PostingPage(total=total, limit=limit, offset=offset, items=rows)


@router.get("/{posting_id}", response_model=PostingDetail)
def get_posting(posting_id: int, db: Annotated[Session, Depends(get_db)]) -> Posting:
    posting = db.get(Posting, posting_id)  # lookup by primary key
    if posting is None:
        raise HTTPException(status_code=404, detail="Posting not found")
    return posting
