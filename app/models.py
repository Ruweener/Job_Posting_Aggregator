"""Database tables, defined as Python classes (SQLAlchemy ORM)."""
from datetime import datetime

from sqlalchemy import ARRAY, Boolean, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Parent class for all models. Base.metadata collects every table,
    which is what Alembic compares against the real database."""


class Posting(Base):
    __tablename__ = "postings"
    # One row per job per board: re-ingesting the same job updates it instead
    # of inserting a duplicate. Postgres enforces this with a unique index.
    __table_args__ = (UniqueConstraint("source", "source_job_id", name="uq_postings_source_job"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    # Where it came from
    source: Mapped[str] = mapped_column(String(20))          # greenhouse | lever | ashby
    source_job_id: Mapped[str] = mapped_column(String(100))  # the board's own ID, stored as text

    # What it is
    company: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(500))
    location: Mapped[str | None] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(Text)
    remote: Mapped[bool] = mapped_column(Boolean, default=False)
    description_text: Mapped[str | None] = mapped_column(Text)
    term: Mapped[str] = mapped_column(String(20), default="Unknown")  # Winter 2027 | Summer 2027 | Unknown

    # When
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # server_default=now() means Postgres fills these in, not Python
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)

    # Filled in by the scoring module in Stage 3
    fit_score: Mapped[int | None] = mapped_column(Integer)
    matched_skills: Mapped[list[str] | None] = mapped_column(ARRAY(Text))

    def __repr__(self) -> str:
        return f"<Posting {self.id} {self.company!r} {self.title!r}>"
