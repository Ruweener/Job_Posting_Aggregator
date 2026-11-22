"""Settings loaded from environment variables (and .env during local dev)."""
import os

from dotenv import load_dotenv

# Reads .env into os.environ. Real environment variables win, which is what
# CI and AWS will use later, so the code never changes between environments.
load_dotenv()


def normalize_database_url(url: str) -> str:
    """Hosted providers (Neon, Supabase, RDS guides) hand out URLs starting "postgresql://"
    or "postgres://". SQLAlchemy reads those as "use psycopg2", which isn't installed;
    this project uses psycopg 3, so name that driver explicitly."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


DATABASE_URL = normalize_database_url(os.environ["DATABASE_URL"])
