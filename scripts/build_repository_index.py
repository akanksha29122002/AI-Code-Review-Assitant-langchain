from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.code_review_assistant.config import settings
from src.code_review_assistant.repository_context import RepositoryContextRetriever


def main() -> int:
    retriever = RepositoryContextRetriever()
    count = retriever.build_index()
    print(f"Indexed {count} document chunks into {settings.repository_index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
