from __future__ import annotations

from src.code_review_assistant.github_commenting import build_inline_comments
from src.code_review_assistant.github_client import GitHubClient
from src.code_review_assistant.github_formatters import format_review_body, sort_findings
from src.code_review_assistant.history_store import ReviewHistoryStore
from src.code_review_assistant.github_models import PullRequestContext
from src.code_review_assistant.models import ReviewFinding, ReviewResult
from src.code_review_assistant.repository_context import RepositoryContextRetriever
from src.code_review_assistant.reviewer import CodeReviewAssistant
from src.code_review_assistant.status_checks import evaluate_review_status
from src.code_review_assistant.config import settings


class GitHubReviewService:
    def __init__(self) -> None:
        self.github = GitHubClient()
        self.assistant = CodeReviewAssistant()
        self.history = ReviewHistoryStore()
        self.retriever = RepositoryContextRetriever()

    def review_pull_request(
        self,
        owner: str,
        repo: str,
        number: int,
        installation_id: int | None = None,
        publish_review: bool = True,
    ) -> ReviewResult:
        context = self._load_pull_request_context(owner, repo, number, installation_id)
        diff_text = self._build_diff_text(context.files)
        result = self.assistant.review(
            repo_context=self._build_repo_context(context),
            retrieved_context=self.retriever.retrieve(
                diff_text=diff_text,
                changed_files=self._build_changed_file_summary(context.files),
                repo_context=self._build_repo_context(context),
            ),
            changed_files=self._build_changed_file_summary(context.files),
            diff_text=diff_text,
            language=self._infer_primary_language(context.files),
            focus_areas=["Correctness", "Security", "Performance", "Testing"],
            include_suggestions=True,
        )
        self.history.save_review(
            source="github_pr",
            title=f"{owner}/{repo}#{number}: {context.title}",
            repository=f"{owner}/{repo}",
            pull_request_number=number,
            dedupe_key=f"github_pr:{owner}/{repo}:{number}:{context.head_sha}",
            result=result,
            raw_input=diff_text,
        )
        if publish_review:
            review_body = format_review_body(result)
            inline_comments = build_inline_comments(result, context)

            try:
                self.github.submit_review(
                    owner=owner,
                    repo=repo,
                    number=number,
                    commit_id=context.head_sha,
                    body=review_body,
                    comments=inline_comments,
                    installation_id=context.installation_id,
                )
            except Exception:
                self.github.create_issue_comment(
                    owner,
                    repo,
                    number,
                    review_body,
                    installation_id=context.installation_id,
                )

            status = evaluate_review_status(result)
            self.github.create_commit_status(
                owner,
                repo,
                context.head_sha,
                state=status.state,
                description=status.description,
                context=settings.github_status_context,
                installation_id=context.installation_id,
            )

        return result

    def _load_pull_request_context(
        self,
        owner: str,
        repo: str,
        number: int,
        installation_id: int | None,
    ) -> PullRequestContext:
        pr = self.github.get_pull_request(owner, repo, number, installation_id)
        files = self.github.list_pull_request_files(owner, repo, number, installation_id)
        return PullRequestContext(
            owner=owner,
            repo=repo,
            number=number,
            title=pr.get("title", ""),
            body=pr.get("body") or "",
            head_sha=pr["head"]["sha"],
            base_ref=pr["base"]["ref"],
            head_ref=pr["head"]["ref"],
            installation_id=installation_id,
            files=files,
        )

    def _build_repo_context(self, context: PullRequestContext) -> str:
        return (
            f"Repository: {context.owner}/{context.repo}\n"
            f"Pull request title: {context.title}\n"
            f"Base branch: {context.base_ref}\n"
            f"Head branch: {context.head_ref}\n"
            f"Pull request description:\n{context.body or 'No PR description provided.'}"
        )

    def _build_changed_file_summary(self, files: list[dict]) -> str:
        parts: list[str] = []
        for item in files:
            parts.append(
                f"- {item['filename']}: status={item.get('status', 'modified')}, "
                f"additions={item.get('additions', 0)}, deletions={item.get('deletions', 0)}"
            )
        return "\n".join(parts) if parts else "No changed files returned by GitHub."

    def _build_diff_text(self, files: list[dict]) -> str:
        chunks: list[str] = []
        for item in files:
            patch = item.get("patch")
            if not patch:
                continue
            chunks.append(f"diff --git a/{item['filename']} b/{item['filename']}\n{patch}")
        return "\n\n".join(chunks) if chunks else "No patch text was returned by GitHub."

    def _infer_primary_language(self, files: list[dict]) -> str:
        counts: dict[str, int] = {}
        for item in files:
            name = item["filename"].lower()
            language = self._language_from_filename(name)
            counts[language] = counts.get(language, 0) + 1
        if not counts:
            return "Unknown"
        return max(counts, key=counts.get)

    def _language_from_filename(self, filename: str) -> str:
        mapping = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".tsx": "TypeScript",
            ".jsx": "JavaScript",
            ".java": "Java",
            ".go": "Go",
            ".rb": "Ruby",
            ".php": "PHP",
            ".cs": "C#",
            ".rs": "Rust",
        }
        for suffix, language in mapping.items():
            if filename.endswith(suffix):
                return language
        return "Unknown"
