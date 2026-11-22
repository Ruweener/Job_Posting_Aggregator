"""Settings loaded from environment variables (and .env during local dev)."""
import os

from dotenv import load_dotenv

# Reads .env into os.environ. Real environment variables win, which is what
# CI and AWS will use later, so the code never changes between environments.
load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
