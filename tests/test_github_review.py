import unittest

from src.code_review_assistant.github_review import GitHubReviewService
from src.code_review_assistant.github_commenting import build_inline_comments, finding_to_comment
from src.code_review_assistant.github_models import PullRequestContext
from src.code_review_assistant.models import ReviewFinding, ReviewResult


class GitHubReviewTests(unittest.TestCase):
    def test_finding_to_comment_matches_changed_line(self) -> None:
        finding = ReviewFinding(
            title="Missing input validation",
            severity="high",
            file_path="src/api.py",
            line_reference="12",
            description="User input is used without validation.",
            impact="This can cause invalid state.",
            recommendation="Validate the payload before use.",
        )
        file_index = {
            "src/api.py": {
                "patch": "@@ -10,0 +10,3 @@\n+first\n+second\n+third\n",
            }
        }

        comment = finding_to_comment(finding, file_index)
        self.assertIsNotNone(comment)
        self.assertEqual(comment["path"], "src/api.py")
        self.assertEqual(comment["line"], 12)

    def test_build_inline_comments_filters_unmatched_findings(self) -> None:
        result = ReviewResult(
            summary="Summary",
            overall_risk="medium",
            findings=[
                ReviewFinding(
                    title="Valid",
                    severity="medium",
                    file_path="src/app.py",
                    line_reference="5",
                    description="Problem",
                    impact="Impact",
                    recommendation="Fix it",
                ),
                ReviewFinding(
                    title="No line",
                    severity="high",
                    file_path="src/app.py",
                    line_reference="50",
                    description="Problem",
                    impact="Impact",
                    recommendation="Fix it",
                ),
            ],
            missing_tests=[],
        )
        context = PullRequestContext(
            owner="octo",
            repo="repo",
            number=1,
            title="PR",
            body="Body",
            head_sha="abc",
            base_ref="main",
            head_ref="feature",
            installation_id=123,
            files=[{"filename": "src/app.py", "patch": "@@ -5,0 +5,2 @@\n+foo\n+bar\n"}],
        )

        comments = build_inline_comments(result, context)
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0]["line"], 5)

    def test_review_pull_request_preview_mode_skips_github_publication(self) -> None:
        result = ReviewResult(
            summary="Summary",
            overall_risk="medium",
            findings=[],
            missing_tests=[],
        )
        context = PullRequestContext(
            owner="octo",
            repo="repo",
            number=7,
            title="PR",
            body="Body",
            head_sha="abc123",
            base_ref="main",
            head_ref="feature",
            installation_id=99,
            files=[{"filename": "src/app.py", "patch": "@@ -1,0 +1,1 @@\n+foo\n"}],
        )

        class FakeAssistant:
            def review(self, **kwargs):
                return result

        class FakeRetriever:
            def retrieve(self, **kwargs):
                return "context"

        class FakeHistory:
            def __init__(self) -> None:
                self.saved = False

            def save_review(self, **kwargs):
                self.saved = True
                return 1

        class FakeGitHub:
            def __init__(self) -> None:
                self.review_calls = 0
                self.comment_calls = 0
                self.status_calls = 0

            def submit_review(self, **kwargs):
                self.review_calls += 1

            def create_issue_comment(self, *args, **kwargs):
                self.comment_calls += 1

            def create_commit_status(self, *args, **kwargs):
                self.status_calls += 1

        service = GitHubReviewService.__new__(GitHubReviewService)
        service.github = FakeGitHub()
        service.assistant = FakeAssistant()
        service.history = FakeHistory()
        service.retriever = FakeRetriever()
        service._load_pull_request_context = lambda *args, **kwargs: context

        reviewed = service.review_pull_request("octo", "repo", 7, publish_review=False)

        self.assertEqual(reviewed, result)
        self.assertTrue(service.history.saved)
        self.assertEqual(service.github.review_calls, 0)
        self.assertEqual(service.github.comment_calls, 0)
        self.assertEqual(service.github.status_calls, 0)


if __name__ == "__main__":
    unittest.main()
