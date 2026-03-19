from __future__ import annotations

from src.code_review_assistant.models import ReviewFinding, ReviewResult


SEVERITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}


def sort_findings(findings: list[ReviewFinding]) -> list[ReviewFinding]:
    return sorted(findings, key=lambda finding: (SEVERITY_ORDER.get(finding.severity, 99), finding.title))


def format_review_body(result: ReviewResult) -> str:
    lines = [
        "## AI Code Review",
        "",
        f"**Summary:** {result.summary}",
        f"**Overall risk:** {result.overall_risk}",
        "",
    ]

    if result.findings:
        lines.append("### Findings")
        lines.append("")
        for idx, finding in enumerate(sort_findings(result.findings), start=1):
            location = ""
            if finding.file_path:
                location = f" (`{finding.file_path}`"
                if finding.line_reference:
                    location += f":{finding.line_reference}"
                location += ")"
            lines.append(f"{idx}. **[{finding.severity.upper()}] {finding.title}**{location}")
            lines.append(f"   - {finding.description}")
            lines.append(f"   - Impact: {finding.impact}")
            if finding.recommendation:
                lines.append(f"   - Recommendation: {finding.recommendation}")
        lines.append("")
    else:
        lines.extend(["### Findings", "", "No significant findings reported.", ""])

    lines.append("### Missing Tests")
    lines.append("")
    if result.missing_tests:
        for item in result.missing_tests:
            lines.append(f"- {item}")
    else:
        lines.append("- No specific missing tests identified.")

    return "\n".join(lines).strip()
