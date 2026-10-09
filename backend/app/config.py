"""
Centralized settings. Every env var used anywhere in the project (across all
3 phases) is declared here via pydantic-settings so nothing is hardcoded and
Phase 2/3 code can just `from app.config import settings`.
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://apagent:apagent@postgres:5432/ap_agent_demo"

    # Ollama Cloud (Phase 2)
    ollama_host: str = "https://ollama.com"
    ollama_api_key: str = ""
    ollama_model: str = "gpt-oss:120b"  # NOTE: no "-cloud" suffix for the hosted API
    # The hosted API rejects bursts of parallel chats. Keep this intentionally
    # conservative: each ingest needs an extraction and an explanation call.
    ollama_max_concurrency: int = Field(default=1, ge=1)
    ollama_max_retries: int = Field(default=3, ge=0)
    ollama_retry_delay_seconds: float = Field(default=2.0, gt=0)

    # An ingest keeps a synchronous SQLAlchemy session open while it obtains
    # the audit explanation. Limit whole requests so a batch submission cannot
    # exhaust PostgreSQL's connection pool before the LLM limiter is reached.
    ingest_max_concurrency: int = Field(default=1, ge=1)

    # CORS / frontend (Phase 2 wires CORSMiddleware, Phase 3 consumes this URL)
    frontend_origin: str = "http://localhost:3000"
    next_public_api_url: str = "http://localhost:8000"

    # Chroma (Phase 2) — deliberately no persistent volume, see PROGRESS.md
    chroma_persist_dir: str = "/app/chroma_data"

    # Mock data seed (Phase 2) — vendors/POs/receipts loaded on startup if empty
    mock_data_path: str = "/mock_data/output/mock_dataset.json"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
