from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.code_review_assistant.fallback_reviewer import fallback_review


def main() -> int:
    sample_path = ROOT / "examples" / "demo_diff.patch"
    diff_text = sample_path.read_text(encoding="utf-8")

    result = fallback_review(
        diff_text=diff_text,
        changed_files="- src/payments.py: adds payment charge helper",
        repo_context="Demo project for the AI Code Review Assistant.",
        language="Python",
        include_suggestions=True,
        failure_reason="demo mode",
    )

    print("# Demo Review Result")
    print("")
    print(f"Summary: {result.summary}")
    print(f"Risk: {result.overall_risk}")
    print("")
    print("Findings:")
    if not result.findings:
        print("- No findings")
    for finding in result.findings:
        location = ""
        if finding.file_path:
            location = f" ({finding.file_path}"
            if finding.line_reference:
                location += f":{finding.line_reference}"
            location += ")"
        print(f"- [{finding.severity}] {finding.title}{location}")
        print(f"  {finding.description}")
        if finding.recommendation:
            print(f"  Fix: {finding.recommendation}")

    print("")
    print("Missing tests:")
    if not result.missing_tests:
        print("- No specific missing tests")
    for item in result.missing_tests:
        print(f"- {item}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
