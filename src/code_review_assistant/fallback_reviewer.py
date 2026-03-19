from __future__ import annotations

import re

from src.code_review_assistant.models import ReviewFinding, ReviewResult


DEBUG_PATTERNS = (
    r"\bprint\s*\(",
    r"\bconsole\.log\s*\(",
    r"\bpdb\.set_trace\s*\(",
    r"\bdebugger\b",
)

SECRET_PATTERNS = (
    r"api[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]",
    r"secret\s*[:=]\s*['\"][^'\"]+['\"]",
    r"password\s*[:=]\s*['\"][^'\"]+['\"]",
    r"token\s*[:=]\s*['\"][^'\"]+['\"]",
)


def _append_finding(findings: list[ReviewFinding], finding: ReviewFinding) -> None:
    key = (finding.title, finding.file_path, finding.line_reference)
    existing_keys = {(item.title, item.file_path, item.line_reference) for item in findings}
    if key not in existing_keys:
        findings.append(finding)


def _infer_language(language: str, diff_text: str, changed_files: str) -> str:
    combined = "\n".join([language, diff_text, changed_files]).lower()
    if "std::" in combined or ".cpp" in combined or ".hpp" in combined or "#include" in combined:
        return "C++"
    if "console.log" in combined or ".ts" in combined or ".js" in combined:
        return "JavaScript"
    if "def " in combined or ".py" in combined:
        return "Python"
    return language or "Unknown"


def _looks_like_missing_semicolon(code_line: str, language: str) -> bool:
    if language not in {"C++", "Java", "JavaScript", "TypeScript", "C#"}:
        return False
    stripped = code_line.strip()
    if not stripped or stripped.startswith("//"):
        return False
    if stripped.endswith((";", "{", "}", ":", ",")):
        return False
    if stripped.startswith(("#", "if ", "for ", "while ", "switch ", "catch ")):
        return False
    if stripped in {"public", "private", "protected"}:
        return False
    return bool(
        re.search(r"\breturn\b", stripped)
        or re.search(r"=", stripped)
        or re.search(r"\)$", stripped)
        or re.search(r"\b(?:int|long|short|double|float|bool|char|string|auto|void)\b", stripped)
    )


def _analyze_code_line(
    *,
    code_line: str,
    language: str,
    include_suggestions: bool,
    findings: list[ReviewFinding],
    current_file: str | None,
    current_line: int | None,
) -> None:
    for pattern in SECRET_PATTERNS:
        if re.search(pattern, code_line, flags=re.IGNORECASE):
            _append_finding(
                findings,
                ReviewFinding(
                    title="Possible hardcoded secret",
                    severity="critical",
                    file_path=current_file,
                    line_reference=str(current_line) if current_line else None,
                    description="Added code appears to contain a hardcoded credential or token.",
                    impact="Secrets committed to code can be leaked and abused immediately.",
                    recommendation=(
                        "Move the secret to environment-based configuration and rotate the exposed value."
                        if include_suggestions
                        else None
                    ),
                ),
            )
            break

    for pattern in DEBUG_PATTERNS:
        if re.search(pattern, code_line):
            _append_finding(
                findings,
                ReviewFinding(
                    title="Debug output left in code",
                    severity="medium",
                    file_path=current_file,
                    line_reference=str(current_line) if current_line else None,
                    description="The change adds debugging output or a debugger hook.",
                    impact="Debug statements can leak data, clutter logs, and suggest unfinished code paths.",
                    recommendation=(
                        "Remove the debug statement or gate it behind non-production diagnostics."
                        if include_suggestions
                        else None
                    ),
                ),
            )
            break

    if _looks_like_missing_semicolon(code_line, language):
        _append_finding(
            findings,
            ReviewFinding(
                title="Likely missing statement terminator",
                severity="high" if language == "C++" else "medium",
                file_path=current_file,
                line_reference=str(current_line) if current_line else None,
                description=(
                    f"The added {language} line looks like a statement that should end with `;`, but it does not."
                ),
                impact="This can cause an immediate compile or parse failure.",
                recommendation=(
                    "Add the missing semicolon or adjust the statement syntax."
                    if include_suggestions
                    else None
                ),
            ),
        )


def fallback_review(
    *,
    diff_text: str,
    changed_files: str,
    repo_context: str,
    language: str,
    include_suggestions: bool,
    failure_reason: str | None = None,
) -> ReviewResult:
    findings: list[ReviewFinding] = []
    language = _infer_language(language, diff_text, changed_files)
    diff_lines = diff_text.splitlines()
    current_file: str | None = None
    current_new_line = 0
    has_diff_markers = any(
        line.startswith("diff --git ") or line.startswith("@@") or line.startswith("+") or line.startswith("-")
        for line in diff_lines
    )

    for raw_line in diff_lines:
        if raw_line.startswith("diff --git "):
            match = re.search(r" b/(.+)$", raw_line)
            current_file = match.group(1) if match else None
            continue

        if raw_line.startswith("@@"):
            match = re.search(r"\+(\d+)", raw_line)
            if match:
                current_new_line = int(match.group(1))
            continue

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            code_line = raw_line[1:]
            _analyze_code_line(
                code_line=code_line,
                language=language,
                include_suggestions=include_suggestions,
                findings=findings,
                current_file=current_file,
                current_line=current_new_line if current_new_line else None,
            )

            current_new_line += 1
            continue

        if raw_line.startswith("-") and not raw_line.startswith("---"):
            continue

        current_new_line += 1

    if not has_diff_markers:
        for index, raw_line in enumerate(diff_lines, start=1):
            _analyze_code_line(
                code_line=raw_line,
                language=language,
                include_suggestions=include_suggestions,
                findings=findings,
                current_file=None,
                current_line=index,
            )

    if "except:" in diff_text or "except Exception:" in diff_text:
        findings.append(
            ReviewFinding(
                title="Broad exception handling",
                severity="medium",
                file_path=None,
                line_reference=None,
                description="The change appears to catch overly broad exceptions.",
                impact="Broad exception handling can hide real failures and make debugging harder.",
                recommendation=(
                    "Catch narrower exception types and log enough context for failures."
                    if include_suggestions
                    else None
                ),
            )
        )

    missing_tests: list[str] = []
    normalized_changed_files = changed_files.lower()
    if normalized_changed_files and "test" not in normalized_changed_files and len(diff_text) > 80:
        missing_tests.append(
            f"Add or update {language} tests that cover the modified code path and its failure cases."
        )

    if findings:
        overall_risk = "high" if any(item.severity == "critical" for item in findings) else "medium"
        summary = "Fallback review found rule-based issues in the submitted change."
    else:
        overall_risk = "low"
        summary = "Fallback review found no obvious rule-based issues in the submitted change."

    if failure_reason:
        summary = f"{summary} External model review was unavailable, so the app used local fallback analysis."

    return ReviewResult(
        summary=summary,
        overall_risk=overall_risk,
        findings=findings,
        missing_tests=missing_tests,
    )
