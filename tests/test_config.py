import pytest

from app.config import normalize_database_url


@pytest.mark.parametrize("url, expected", [
    ("postgresql://u:p@ep-x.neon.tech/db?sslmode=require", "postgresql+psycopg://u:p@ep-x.neon.tech/db?sslmode=require"),
    ("postgres://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
    ("postgresql+psycopg://u:p@localhost:5433/db", "postgresql+psycopg://u:p@localhost:5433/db"),  # unchanged
])
def test_normalize_database_url(url, expected):
    assert normalize_database_url(url) == expected
