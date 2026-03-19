from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.code_review_assistant.config import settings


def is_placeholder(value: str | None) -> bool:
    if not value:
        return True
    normalized = value.strip().lower()
    return (
        normalized.startswith("your_")
        or normalized.startswith("replace_with_")
        or "your_real_" in normalized
        or normalized in {"changeme", "replace-me"}
    )


def main() -> int:
    issues: list[str] = []

    print("Setup validation")
    print("")

    print(f"OK  LLM_PROVIDER = {settings.llm_provider}")

    if settings.llm_provider.lower() == "openai":
        if settings.openai_api_key and not is_placeholder(settings.openai_api_key):
            print("OK  OPENAI_API_KEY is set")
        else:
            issues.append("OPENAI_API_KEY is missing or still set to the template placeholder")
            print("ERR OPENAI_API_KEY is missing or still set to the template placeholder")
    elif settings.llm_provider.lower() == "gemini":
        if settings.gemini_api_key and not is_placeholder(settings.gemini_api_key):
            print("OK  GEMINI_API_KEY is set")
            print(f"OK  GEMINI_MODEL = {settings.gemini_model}")
            print(f"OK  GEMINI_EMBEDDING_MODEL = {settings.gemini_embedding_model}")
        else:
            issues.append("GEMINI_API_KEY is missing or still set to the template placeholder")
            print("ERR GEMINI_API_KEY is missing or still set to the template placeholder")
    elif settings.llm_provider.lower() == "ollama":
        print(f"OK  OLLAMA_BASE_URL = {settings.ollama_base_url}")
        print(f"OK  OLLAMA_MODEL = {settings.ollama_model}")
        print(f"OK  OLLAMA_EMBEDDING_MODEL = {settings.ollama_embedding_model}")
    else:
        issues.append(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
        print(f"ERR Unsupported LLM_PROVIDER: {settings.llm_provider}")

    if settings.uses_github_app:
        print("OK  GitHub App mode selected")
        if settings.github_app_id:
            print(f"OK  GITHUB_APP_ID is set: {settings.github_app_id}")
        if settings.github_private_key_path:
            key_path = Path(settings.github_private_key_path)
            if key_path.exists():
                print(f"OK  GITHUB_PRIVATE_KEY_PATH exists: {key_path}")
            else:
                issues.append(f"GITHUB_PRIVATE_KEY_PATH does not exist: {key_path}")
                print(f"ERR GITHUB_PRIVATE_KEY_PATH does not exist: {key_path}")
        try:
            private_key = settings.github_private_key
        except Exception as exc:
            issues.append(str(exc))
            print(f"ERR {exc}")
        else:
            if private_key:
                print("OK  GitHub private key loaded")
            else:
                issues.append("GitHub App private key could not be loaded")
                print("ERR GitHub App private key could not be loaded")

        if settings.github_installation_id:
            print(f"OK  GITHUB_INSTALLATION_ID is set: {settings.github_installation_id}")
        else:
            print("WARN GITHUB_INSTALLATION_ID is not set; the app will try to resolve it per repository")
    elif settings.github_token and not is_placeholder(settings.github_token):
        print("OK  GITHUB_TOKEN is set")
    else:
        issues.append("GitHub auth is not configured or still set to the template placeholder")
        print("ERR GitHub auth is not configured or still set to the template placeholder")

    if settings.github_webhook_secret and not is_placeholder(settings.github_webhook_secret):
        print("OK  GITHUB_WEBHOOK_SECRET is set")
    else:
        print("WARN GITHUB_WEBHOOK_SECRET is not set or still a placeholder; webhook signature verification will be skipped")

    print(f"OK  GITHUB_API_URL = {settings.github_api_url}")
    print(f"OK  GITHUB_STATUS_CONTEXT = {settings.github_status_context}")
    print(f"OK  GITHUB_STATUS_FAIL_SEVERITY = {settings.github_status_fail_severity}")
    print(f"OK  OPENAI_MODEL = {settings.openai_model}")
    print(f"OK  OPENAI_EMBEDDING_MODEL = {settings.openai_embedding_model}")
    print(f"OK  OPENAI_TEMPERATURE = {settings.temperature}")
    print(f"OK  REVIEW_HISTORY_DB_PATH = {settings.review_history_db_path}")
    print(f"OK  REPOSITORY_INDEX_PATH = {settings.repository_index_path}")
    print("")

    if issues:
        print("Validation failed")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("Validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
