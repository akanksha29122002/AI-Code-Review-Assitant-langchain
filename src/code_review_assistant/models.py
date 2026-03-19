from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Severity = Literal["low", "medium", "high", "critical"]
RiskLevel = Literal["low", "medium", "high"]


class ReviewFinding(BaseModel):
    title: str = Field(description="Short bug or risk title.")
    severity: Severity = Field(description="Priority of the issue.")
    file_path: str | None = Field(default=None, description="Relevant file path if available.")
    line_reference: str | None = Field(
        default=None,
        description="Relevant new-file line number or hunk reference if available.",
    )
    description: str = Field(description="Concrete explanation of the issue.")
    impact: str = Field(description="Why the issue matters.")
    recommendation: str | None = Field(default=None, description="Suggested fix or mitigation.")


class ReviewResult(BaseModel):
    summary: str = Field(description="High-level review summary.")
    overall_risk: RiskLevel = Field(description="Overall change risk level.")
    findings: list[ReviewFinding] = Field(default_factory=list, description="Ranked review findings.")
    missing_tests: list[str] = Field(default_factory=list, description="Test scenarios that should be added.")


class ReviewHistoryRecord(BaseModel):
    id: int
    source: str
    title: str
    repository: str | None = None
    pull_request_number: int | None = None
    overall_risk: str
    summary: str
    findings_count: int
    missing_tests_count: int
    created_at: str
