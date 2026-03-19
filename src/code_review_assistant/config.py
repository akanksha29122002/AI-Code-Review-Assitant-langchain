from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover
    def load_dotenv() -> bool:
        return False


load_dotenv(override=True)


class Settings:
    """Runtime settings sourced from environment variables."""

    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    openai_embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    gemini_embedding_model: str = os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004")
    temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0"))
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    ollama_embedding_model: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    github_token: str | None = os.getenv("GITHUB_TOKEN")
    github_webhook_secret: str | None = os.getenv("GITHUB_WEBHOOK_SECRET")
    github_api_url: str = os.getenv("GITHUB_API_URL", "https://api.github.com")
    github_status_context: str = os.getenv("GITHUB_STATUS_CONTEXT", "ai-code-review")
    github_status_fail_severity: str = os.getenv("GITHUB_STATUS_FAIL_SEVERITY", "high")
    github_app_id: str | None = os.getenv("GITHUB_APP_ID")
    github_installation_id: str | None = os.getenv("GITHUB_INSTALLATION_ID")
    github_private_key_path: str | None = os.getenv("GITHUB_PRIVATE_KEY_PATH")
    review_history_db_path: str = os.getenv("REVIEW_HISTORY_DB_PATH", "data/review_history.db")
    repository_index_path: str = os.getenv("REPOSITORY_INDEX_PATH", "data/repository_index.json")

    @property
    def github_private_key(self) -> str | None:
        if not self.github_private_key_path:
            return None
        path = Path(self.github_private_key_path)
        if not path.exists():
            raise ValueError(f"GITHUB_PRIVATE_KEY_PATH does not exist: {path}")
        return path.read_text(encoding="utf-8")

    @property
    def uses_github_app(self) -> bool:
        return bool(self.github_app_id and self.github_private_key_path)


settings = Settings()
