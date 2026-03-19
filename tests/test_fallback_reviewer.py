import unittest

from src.code_review_assistant.fallback_reviewer import fallback_review
from src.code_review_assistant.reviewer import CodeReviewAssistant


class FallbackReviewerTests(unittest.TestCase):
    def test_fallback_review_finds_debug_output_and_missing_tests(self) -> None:
        result = fallback_review(
            diff_text="""diff --git a/src/app.py b/src/app.py
@@ -1,0 +1,2 @@
+print("debug")
+return value
""",
            changed_files="- src/app.py: updated main flow",
            repo_context="",
            language="Python",
            include_suggestions=True,
            failure_reason="quota",
        )
        self.assertEqual(result.overall_risk, "medium")
        self.assertEqual(len(result.findings), 1)
        self.assertIn("fallback", result.summary.lower())
        self.assertEqual(len(result.missing_tests), 1)

    def test_assistant_falls_back_when_chain_raises(self) -> None:
        assistant = CodeReviewAssistant.__new__(CodeReviewAssistant)
        assistant.chain = type(
            "BrokenChain",
            (),
            {"invoke": staticmethod(lambda payload: (_ for _ in ()).throw(ValueError("quota exceeded")))}
        )()
        assistant.initialization_error = None

        result = assistant.review(
            repo_context="",
            retrieved_context="",
            changed_files="- src/app.py",
            diff_text='diff --git a/src/app.py b/src/app.py\n@@ -1,0 +1,1 @@\n+console.log("x")\n',
            language="JavaScript",
            focus_areas=["Correctness"],
            include_suggestions=True,
        )

        self.assertEqual(result.overall_risk, "medium")
        self.assertTrue(result.findings)

    def test_fallback_review_flags_likely_missing_cpp_semicolon(self) -> None:
        result = fallback_review(
            diff_text="""diff --git a/main.cpp b/main.cpp
@@ -1,0 +1,2 @@
+std::vector<int> result = sol.twoSum(nums, target)
+return 0;
""",
            changed_files="- main.cpp: add example usage",
            repo_context="",
            language="Python",
            include_suggestions=True,
            failure_reason="quota",
        )
        self.assertTrue(any(item.title == "Likely missing statement terminator" for item in result.findings))
        self.assertEqual(result.overall_risk, "medium")

    def test_fallback_review_flags_missing_semicolon_in_raw_cpp_snippet(self) -> None:
        result = fallback_review(
            diff_text="""class Solution {
public:
    int main() {
        std::vector<int> result = sol.twoSum(nums, target)
        return 0;
    }
};""",
            changed_files="",
            repo_context="",
            language="Python",
            include_suggestions=True,
            failure_reason="quota",
        )
        self.assertTrue(any(item.title == "Likely missing statement terminator" for item in result.findings))


if __name__ == "__main__":
    unittest.main()
