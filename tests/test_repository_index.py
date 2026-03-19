import json
import unittest
from pathlib import Path

from src.code_review_assistant.repository_context import (
    RepositoryContextRetriever,
    chunk_text,
    cosine_similarity,
)


class FakeEmbeddingProvider:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, float(index + 1)] for index, _ in enumerate(texts)]

    def embed_query(self, text: str) -> list[float]:
        return [1.0, 2.0]


class RepositoryIndexTests(unittest.TestCase):
    def test_chunk_text_splits_large_input(self) -> None:
        chunks = chunk_text("a" * 4000, chunk_size=1800, overlap=200)
        self.assertGreater(len(chunks), 1)

    def test_cosine_similarity_returns_expected_value(self) -> None:
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0)
        self.assertEqual(cosine_similarity([1.0], [1.0, 1.0]), 0.0)

    def test_build_and_use_repository_index(self) -> None:
        repo_root = Path("tests/_temp_index_repo")
        index_path = Path("tests/_temp_repository_index.json")
        repo_root.mkdir(parents=True, exist_ok=True)
        file_path = repo_root / "src" / "reviewer.py"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("def check_permissions(user):\n    return user.is_admin\n", encoding="utf-8")

        try:
            retriever = RepositoryContextRetriever(
                str(repo_root),
                index_path=str(index_path),
                max_files=1,
                embedding_provider=FakeEmbeddingProvider(),
            )
            count = retriever.build_index()
            self.assertGreater(count, 0)
            payload = json.loads(index_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["documents"])

            result = retriever.retrieve(
                diff_text="security review for reviewer permissions",
                changed_files="- src/reviewer.py: update permissions logic",
                repo_context="authorization bug",
            )
            self.assertIn("File: src/reviewer.py#chunk-1", result)
        finally:
            if file_path.exists():
                file_path.unlink()
            if file_path.parent.exists():
                file_path.parent.rmdir()
            if repo_root.exists():
                repo_root.rmdir()
            if index_path.exists():
                index_path.unlink()
