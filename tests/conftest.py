"""Shared pytest fixtures. pytest loads conftest.py automatically.

Database tests run against a SEPARATE database (jobagg_test by default), never the dev one.
  - The test database is created if missing and migrated with Alembic once per test run,
    so the migrations themselves are tested too.
  - Every test runs inside a transaction that is rolled back afterwards, so tests can't
    affect each other and the database is empty at the start of each test.
  - If Postgres isn't running, database tests are skipped (parser/filter tests still run).
"""
import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import DATABASE_URL
from app.main import app

# CI (Stage 4) sets TEST_DATABASE_URL; locally we reuse the dev server with a _test database
TEST_DATABASE_URL = make_url(
    os.environ.get("TEST_DATABASE_URL")
    or make_url(DATABASE_URL).set(database=make_url(DATABASE_URL).database + "_test")
)


_db_unavailable: str | None = None  # remembered so we only wait for a dead server once


def _create_database_if_missing(url) -> None:
    # CREATE DATABASE can't run inside a transaction, hence AUTOCOMMIT, and it must be run
    # from a different database: "postgres" is the default one every server has.
    # connect_timeout keeps the "is Postgres running?" check from hanging.
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT",
                          connect_args={"connect_timeout": 3})
    with admin.connect() as conn:
        exists = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :name"),
                             {"name": url.database})
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()


@pytest.fixture(scope="session")  # session scope: runs once for the whole test run
def db_engine():
    global _db_unavailable
    if _db_unavailable:
        pytest.skip(_db_unavailable)
    try:
        _create_database_if_missing(TEST_DATABASE_URL)
    except OperationalError:
        _db_unavailable = f"Postgres not reachable at {TEST_DATABASE_URL.host}:{TEST_DATABASE_URL.port}"
        pytest.skip(_db_unavailable)

    cfg = Config("alembic.ini")
    url = TEST_DATABASE_URL.render_as_string(hide_password=False)
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(cfg, "head")

    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """A session whose work is rolled back after the test.
    join_transaction_mode="create_savepoint" turns the code's own session.commit() calls
    into savepoints inside our outer transaction, so even committed data is undone."""
    connection = db_engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    outer.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """FastAPI test client whose endpoints use the test session instead of the dev database."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
