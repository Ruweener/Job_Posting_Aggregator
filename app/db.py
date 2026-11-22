"""Database engine and session factory shared by the whole app."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL

# The engine owns a pool of connections to Postgres. Create it once per process.
# pool_pre_ping checks a connection is alive before using it.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# SessionLocal() gives a Session: a unit of work that tracks changes and
# sends them to the database on commit().
SessionLocal = sessionmaker(bind=engine)
