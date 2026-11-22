"""Shared FastAPI dependencies."""
from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.db import SessionLocal


def get_db() -> Iterator[Session]:
    """One database session per request. FastAPI runs the code before `yield` when the
    request starts and the `finally` block after the response is sent, so the session
    is always closed, even if the endpoint raises an error."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
