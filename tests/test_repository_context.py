import unittest
from pathlib import Path

from src.code_review_assistant.repository_context import RepositoryContextRetriever


class RepositoryContextTests(unittest.TestCase):
    def test_retrieve_prefers_hint_path_matches(self) -> None:
        repo_root = Path("tests/_temp_repo_context")
        repo_root.mkdir(parents=True, exist_ok=True)
        target = repo_root / "src" / "service.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("def validate_user_input(value):\n    return value.strip()\n", encoding="utf-8")
        other = repo_root / "README.md"
        other.write_text("General project documentation", encoding="utf-8")

        try:
            retriever = RepositoryContextRetriever(str(repo_root), max_files=1)
            result = retriever.retrieve(
                diff_text="diff --git a/src/service.py b/src/service.py\n+validate_user_input(payload)",
                changed_files="- src/service.py: update validation",
                repo_context="validation bug in service layer",
            )
            self.assertIn("File: src/service.py", result)
        finally:
            if target.exists():
                target.unlink()
            if other.exists():
                other.unlink()
            if target.parent.exists():
                target.parent.rmdir()
            if repo_root.exists():
                repo_root.rmdir()


if __name__ == "__main__":
    unittest.main()
