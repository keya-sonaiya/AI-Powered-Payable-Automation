"""
FastAPI app entrypoint. Registers every router, wires CORSMiddleware for
FRONTEND_ORIGIN, and — since this demo has no Alembic (see PROGRESS.md) —
runs Base.metadata.create_all() plus a one-time mock-data seed on startup.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import models  # noqa: F401 — import registers models on Base before create_all
from app.db.database import Base, engine
from app.db.seed import seed_if_empty
from app.routers import audit, ingest, invoices, metrics

app = FastAPI(
    title="AP Agent Demo",
    description="Invoice intake -> OCR -> LLM extraction -> 3-way match -> policy guardrails -> audit trail.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, tags=["ingest"])
app.include_router(invoices.router, tags=["invoices"])
app.include_router(audit.router, tags=["audit"])
app.include_router(metrics.router, tags=["metrics"])


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    seed_if_empty()


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
