import unittest
from pathlib import Path

from src.code_review_assistant.history_store import ReviewHistoryStore
from src.code_review_assistant.models import ReviewFinding, ReviewResult


class HistoryStoreTests(unittest.TestCase):
    def test_save_and_list_recent_reviews(self) -> None:
        db_path = Path("data/test_review_history.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if db_path.exists():
            db_path.unlink()

        store = ReviewHistoryStore(str(db_path))
        result = ReviewResult(
            summary="Stored summary",
            overall_risk="medium",
            findings=[
                ReviewFinding(
                    title="Issue",
                    severity="high",
                    description="Description",
                    impact="Impact",
                    recommendation="Recommendation",
                )
            ],
            missing_tests=["Add API validation test"],
        )

        review_id = store.save_review(
            source="manual",
            title="Manual review",
            result=result,
            raw_input="diff --git ...",
        )

        self.assertGreater(review_id, 0)
        records = store.list_recent_reviews(limit=5)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].title, "Manual review")
        self.assertEqual(records[0].findings_count, 1)
        self.assertEqual(records[0].missing_tests_count, 1)

    def test_init_creates_parent_directory_for_custom_db_path(self) -> None:
        db_path = Path("data/nested/test_review_history.db")
        if db_path.exists():
            db_path.unlink()
        if db_path.parent.exists():
            db_path.parent.rmdir()

        store = ReviewHistoryStore(str(db_path))

        self.assertTrue(store.db_path.exists())


if __name__ == "__main__":
    unittest.main()
