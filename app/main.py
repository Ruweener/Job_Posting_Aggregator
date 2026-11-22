"""FastAPI application.

Run the API locally:  uvicorn app.main:app --reload
Interactive docs:     http://127.0.0.1:8000/docs
"""
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import postings
from app.api.deps import get_db

app = FastAPI(
    title="Internship Posting Aggregator",
    description="Internship postings from Greenhouse, Lever and Ashby, stored in PostgreSQL.",
    version="0.2.0",
)


@app.get("/health", tags=["meta"])
def health(db: Session = Depends(get_db)) -> dict:
    """Liveness check that also proves the database is reachable."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


app.include_router(postings.router)
