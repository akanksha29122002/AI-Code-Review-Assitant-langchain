import unittest
from pathlib import Path

from src.code_review_assistant.history_store import ReviewHistoryStore
from src.code_review_assistant.models import ReviewResult


class WebhookDedupTests(unittest.TestCase):
    def test_mark_delivery_processed_rejects_duplicates(self) -> None:
        db_path = Path("data/test_delivery_history.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if db_path.exists():
            db_path.unlink()

        store = ReviewHistoryStore(str(db_path))
        self.assertTrue(store.mark_delivery_processed("delivery-1"))
        self.assertFalse(store.mark_delivery_processed("delivery-1"))

    def test_save_review_rejects_duplicate_dedupe_key(self) -> None:
        db_path = Path("data/test_dedupe_history.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if db_path.exists():
            db_path.unlink()

        store = ReviewHistoryStore(str(db_path))
        result = ReviewResult(summary="Summary", overall_risk="low")

        first = store.save_review(
            source="github_pr",
            title="PR Review",
            repository="octo/repo",
            pull_request_number=1,
            dedupe_key="github_pr:octo/repo:1:sha1",
            result=result,
        )
        second = store.save_review(
            source="github_pr",
            title="PR Review",
            repository="octo/repo",
            pull_request_number=1,
            dedupe_key="github_pr:octo/repo:1:sha1",
            result=result,
        )

        self.assertIsNotNone(first)
        self.assertIsNone(second)


if __name__ == "__main__":
    unittest.main()
