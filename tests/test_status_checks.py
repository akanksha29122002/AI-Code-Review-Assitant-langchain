import unittest

from src.code_review_assistant.models import ReviewFinding, ReviewResult
from src.code_review_assistant.status_checks import evaluate_review_status


class StatusCheckTests(unittest.TestCase):
    def test_high_severity_finding_fails_status(self) -> None:
        result = ReviewResult(
            summary="Summary",
            overall_risk="medium",
            findings=[
                ReviewFinding(
                    title="Critical auth issue",
                    severity="high",
                    description="Description",
                    impact="Impact",
                    recommendation="Recommendation",
                )
            ],
        )
        status = evaluate_review_status(result)
        self.assertEqual(status.state, "failure")

    def test_high_risk_without_findings_fails_status(self) -> None:
        result = ReviewResult(summary="Summary", overall_risk="high", findings=[])
        status = evaluate_review_status(result)
        self.assertEqual(status.state, "failure")

    def test_clean_review_succeeds(self) -> None:
        result = ReviewResult(summary="Summary", overall_risk="low", findings=[])
        status = evaluate_review_status(result)
        self.assertEqual(status.state, "success")


if __name__ == "__main__":
    unittest.main()
