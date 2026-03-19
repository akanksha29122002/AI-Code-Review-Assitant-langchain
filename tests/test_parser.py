import unittest

from src.code_review_assistant.parser import extract_added_lines, normalize_list, parse_line_reference


class ParserTests(unittest.TestCase):
    def test_normalize_list_skips_empty_values(self) -> None:
        self.assertEqual(normalize_list(["Security", " ", "Testing"]), "Security, Testing")

    def test_parse_line_reference_extracts_first_integer(self) -> None:
        self.assertEqual(parse_line_reference("line 42 in new file"), 42)

    def test_extract_added_lines_tracks_new_file_line_numbers(self) -> None:
        patch = """@@ -10,2 +10,4 @@
+added zero
+added one
+added two
 unchanged
-removed old
+added three
"""
        self.assertEqual(extract_added_lines(patch), {10, 11, 12, 14})


if __name__ == "__main__":
    unittest.main()
