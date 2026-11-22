"""Quick connectivity check: python -m app.check_db"""
from sqlalchemy import text

from app.db import engine

with engine.connect() as conn:
    version = conn.execute(text("SELECT version()")).scalar_one()
    print("Connected:", version)
