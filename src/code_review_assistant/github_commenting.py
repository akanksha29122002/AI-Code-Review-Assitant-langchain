from __future__ import annotations

from src.code_review_assistant.github_formatters import sort_findings
from src.code_review_assistant.github_models import PullRequestContext
from src.code_review_assistant.models import ReviewFinding, ReviewResult
from src.code_review_assistant.parser import extract_added_lines, parse_line_reference


def build_inline_comments(
    result: ReviewResult,
    context: PullRequestContext,
) -> list[dict]:
    file_index = {item["filename"]: item for item in context.files}
    comments: list[dict] = []
    for finding in sort_findings(result.findings):
        comment = finding_to_comment(finding, file_index)
        if comment:
            comments.append(comment)
    return comments[:10]


def finding_to_comment(finding: ReviewFinding, file_index: dict[str, dict]) -> dict | None:
    if not finding.file_path or not finding.line_reference:
        return None
    if finding.file_path not in file_index:
        return None

    line_number = parse_line_reference(finding.line_reference)
    if line_number is None:
        return None

    changed_lines = extract_added_lines(file_index[finding.file_path].get("patch") or "")
    if line_number not in changed_lines:
        return None

    body = f"[{finding.severity.upper()}] {finding.title}\n\n{finding.description}"
    if finding.recommendation:
        body += f"\n\nRecommendation: {finding.recommendation}"

    return {
        "path": finding.file_path,
        "line": line_number,
        "side": "RIGHT",
        "body": body,
    }
