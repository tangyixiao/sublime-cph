import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from CompetitiveHelper.competitive_helper_core import (
    build_head_comments,
    format_cpp,
    import_problem,
    slugify,
)


class ImportProblemTests(unittest.TestCase):
    def test_uses_template_js_filename_rules_for_codeforces(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template = root / "template.cpp"
            template.write_text("// personal template\n", encoding="utf-8")
            data = {
                "name": "A. Two Sum",
                "url": "https://codeforces.com/contest/123/problem/A",
                "tests": [],
            }

            result = import_problem(data, root, template)

            self.assertEqual(result["name"], "CF123A Two Sum")
            self.assertEqual(result["source"], str(root / "CF123A Two Sum.cpp"))
            self.assertEqual(
                result["sample_dir"], str(root / "cph" / "CF123A Two Sum")
            )

    def test_uses_template_js_provider_ids(self):
        cases = [
            (
                "P1001 A+B",
                "https://www.luogu.com.cn/problem/P1001",
                "P1001 A+B",
            ),
            (
                "A. Problem",
                "https://atcoder.jp/contests/abc123/tasks/abc123_a",
                "ABC123A A. Problem",
            ),
            (
                "Problem",
                "http://poj.org/problem?id=1000",
                "POJ1000 Problem",
            ),
            (
                "Problem",
                "https://onlinejudge.org/problem/100",
                "UVA100 Problem",
            ),
        ]

        for name, url, expected in cases:
            with self.subTest(url=url):
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    template = root / "template.cpp"
                    template.write_text("// personal template\n", encoding="utf-8")
                    result = import_problem(
                        {"name": name, "url": url, "tests": []}, root, template
                    )
                    self.assertEqual(result["name"], expected)
                    self.assertEqual(
                        result["source"], str(root / (expected + ".cpp"))
                    )

    def test_imports_all_samples_and_copies_template(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template = root / "template.cpp"
            template.write_text("// personal template\n", encoding="utf-8")
            data = {
                "name": "A+B",
                "group": "Codeforces - Sample",
                "url": "https://example.test/problem",
                "timeLimit": 1000,
                "memoryLimit": 256,
                "tests": [
                    {"input": "1 2\n", "output": "3\n"},
                    {"input": "10 20\n", "output": "30\n"},
                ],
            }

            result = import_problem(data, root, template)

            self.assertEqual(result["test_count"], 2)
            source = Path(result["source"]).read_text(encoding="utf-8")
            self.assertTrue(source.startswith("//  Author: Tangyixiao\n"))
            self.assertIn("//  Problem: A+B\n", source)
            self.assertIn("//  Contest: Codeforces - Sample\n", source)
            self.assertIn("//  URL: https://example.test/problem\n", source)
            self.assertIn("//  Memory Limit: 256 MB\n", source)
            self.assertIn("//  Time Limit: 1000 ms\n", source)
            self.assertIn("//  Algorithm: \n//  Complexity: O()\n//  Note: \n", source)
            self.assertNotIn("Powered by CP Editor", source)
            self.assertTrue(source.endswith("// personal template\n"))
            sample_dir = root / "cph" / "A+B"
            self.assertEqual((sample_dir / "A+B_1.in").read_text(encoding="utf-8"), "1 2\n")
            self.assertEqual((sample_dir / "A+B_1.ans").read_text(encoding="utf-8"), "3\n")
            self.assertEqual((sample_dir / "A+B_2.in").read_text(encoding="utf-8"), "10 20\n")
            self.assertEqual((sample_dir / "A+B_2.ans").read_text(encoding="utf-8"), "30\n")
            self.assertEqual((sample_dir / "input.txt").read_text(encoding="utf-8"), "1 2\n")
            self.assertEqual((sample_dir / "expected.txt").read_text(encoding="utf-8"), "3\n")
            saved = json.loads((sample_dir / "problem.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["url"], data["url"])
            self.assertEqual(len(saved["tests"]), 2)

    def test_does_not_overwrite_existing_solution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template = root / "template.cpp"
            template.write_text("new template\n", encoding="utf-8")
            source = root / "Existing.cpp"
            source.write_text("my code\n", encoding="utf-8")
            data = {"name": "Existing", "tests": []}

            import_problem(data, root, template)

            self.assertEqual(source.read_text(encoding="utf-8"), "my code\n")

    def test_slugify_removes_path_separators(self):
        self.assertEqual(slugify("A/B: C\\D"), "A_B_ C_D")

    def test_build_head_comments_matches_cp_editor_fields(self):
        data = {
            "name": "A+B",
            "group": "Codeforces Round",
            "url": "https://codeforces.com/contest/1/problem/A",
            "memoryLimit": 256,
            "timeLimit": 2000,
            "interactive": False,
            "testType": "single",
            "batch": {"id": "batch-1"},
        }

        header = build_head_comments(data, now=datetime(2026, 9, 21, 14, 30, 0))

        self.assertEqual(
            header,
            "//  Author: Tangyixiao\n"
            "//  Time: 2026-09-21 14:30:00\n"
            "//  Problem: A+B\n"
            "//  Contest: Codeforces Round\n"
            "//  URL: https://codeforces.com/contest/1/problem/A\n"
            "//  Memory Limit: 256 MB\n"
            "//  Time Limit: 2000 ms\n"
            "//  Interactive: false\n"
            "//  Test Type: single\n"
            "//  Batch ID: batch-1\n"
            "//\n"
            "//  Algorithm: \n"
            "//  Complexity: O()\n"
            "//  Note: \n"
            "\n",
        )

    def test_format_cpp_uses_clang_format_file_style(self):
        source = "int main(){return 0;}\n"

        formatted = format_cpp(source, "example.cpp")

        self.assertEqual(formatted, "int main() { return 0; }\n")


if __name__ == "__main__":
    unittest.main()
