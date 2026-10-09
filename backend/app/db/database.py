"""
SQLAlchemy engine + session factory. Reads DATABASE_URL from app.config so
this is the ONLY place in the codebase that opens a connection to Postgres,
per the project's "FastAPI is the single source of truth" rule.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency (Phase 2 wires this into routers)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
