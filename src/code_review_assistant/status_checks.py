from __future__ import annotations

from dataclasses import dataclass

from src.code_review_assistant.config import settings
from src.code_review_assistant.models import ReviewResult


SEVERITY_ORDER = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}


@dataclass
class ReviewStatus:
    state: str
    description: str
    target_url: str | None = None


def evaluate_review_status(result: ReviewResult) -> ReviewStatus:
    fail_threshold = SEVERITY_ORDER.get(settings.github_status_fail_severity.lower(), 2)
    max_finding_severity = max((SEVERITY_ORDER.get(item.severity, 0) for item in result.findings), default=0)

    if max_finding_severity >= fail_threshold:
        return ReviewStatus(
            state="failure",
            description=f"Review flagged {len(result.findings)} finding(s); at least one is {settings.github_status_fail_severity}+.",
        )

    if result.overall_risk == "high":
        return ReviewStatus(
            state="failure",
            description="Review marked the change as high risk.",
        )

    if result.findings:
        return ReviewStatus(
            state="success",
            description=f"Review completed with {len(result.findings)} lower-severity finding(s).",
        )

    return ReviewStatus(
        state="success",
        description="Review completed with no significant findings.",
    )
