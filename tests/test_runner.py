import tempfile
import unittest
from pathlib import Path

from CompetitiveHelper.cph_runner import run_samples
from CompetitiveHelper.cph_file_io import detect_file_io


class RunnerTests(unittest.TestCase):
    def _write_program(self, root, body):
        source = root / "solution.cpp"
        source.write_text(body, encoding="utf-8")
        samples = root / "cph" / "solution"
        samples.mkdir(parents=True)
        return source, samples

    def test_runs_and_checks_every_sample(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, samples = self._write_program(
                root,
                '#include <iostream>\nint main(){int a,b; std::cin>>a>>b; std::cout<<a+b<<"\\n";}\n',
            )
            (samples / "solution_1.in").write_text("1 2\n", encoding="utf-8")
            (samples / "solution_1.ans").write_text("3\n", encoding="utf-8")
            (samples / "solution_2.in").write_text("10 20\n", encoding="utf-8")
            (samples / "solution_2.ans").write_text("30\n", encoding="utf-8")

            report = run_samples(source, samples, compiler="c++", timeout=2)

            self.assertTrue(report["compiled"])
            self.assertEqual(report["passed"], 2)
            self.assertEqual(report["failed"], 0)

    def test_reports_wrong_answer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, samples = self._write_program(
                root,
                '#include <iostream>\nint main(){std::cout<<"wrong\\n";}\n',
            )
            (samples / "solution_1.in").write_text("", encoding="utf-8")
            (samples / "solution_1.ans").write_text("right\n", encoding="utf-8")

            report = run_samples(source, samples, compiler="c++", timeout=2)

            self.assertEqual(report["passed"], 0)
            self.assertEqual(report["failed"], 1)
            self.assertEqual(report["cases"][0]["status"], "WA")

    def test_reports_timeout(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, samples = self._write_program(
                root,
                '#include <chrono>\n#include <thread>\nint main(){std::this_thread::sleep_for(std::chrono::seconds(2));}\n',
            )
            (samples / "solution_1.in").write_text("", encoding="utf-8")
            (samples / "solution_1.ans").write_text("", encoding="utf-8")

            report = run_samples(source, samples, compiler="c++", timeout=0.1)

            self.assertEqual(report["cases"][0]["status"], "TLE")

    def test_uses_literal_redirects_and_keeps_each_case_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, samples = self._write_program(
                root,
                '#include <cstdio>\n#define BASE "contest"\n'
                'int main(){std::freopen(BASE ".in","r",stdin);'
                'std::freopen(BASE ".out","a",stdout); int n;'
                'std::scanf("%d", &n); std::printf("%d", n * 2); return 0;}\n',
            )
            for n in (1, 2):
                (samples / ("case_{}.in".format(n))).write_text(str(n), encoding="utf-8")
                (samples / ("case_{}.ans".format(n))).write_text(str(n * 2), encoding="utf-8")

            report = run_samples(source, samples)

            self.assertEqual(report["file_io"], {"input": "contest.in", "output": "contest.out"})
            self.assertEqual(report["passed"], 2)
            self.assertEqual((samples / "case_2.out").read_text(encoding="utf-8"), "4")
            self.assertFalse((root / "contest.out").exists())

    def test_detects_only_the_enabled_template_file_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "带 空格.cpp"
            source.write_text(
                '#define FILE_NAME "demo"\n#define FILE_INDEX 4\n'
                '#if JUDGE_TYPE == 1\nJudge_File(FILE_NAME);\n'
                '#elif JUDGE_TYPE == 2\nLocal_File(FILE_NAME, FILE_INDEX);\n#endif\n'
                '// freopen("ignored.in", "r", stdin);\n',
                encoding="utf-8",
            )
            for mode, prefix in ((0, None), (1, "demo"), (2, "demo4")):
                with self.subTest(mode=mode):
                    names = detect_file_io(
                        str(source), str(root), "c++", ["-DJUDGE_TYPE={}".format(mode)]
                    )
                    self.assertEqual(names["input"], prefix + ".in" if prefix else None)
                    self.assertEqual(names["output"], prefix + ".out" if prefix else None)

    def test_explicit_file_names_and_missing_answer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, samples = self._write_program(
                root,
                '#include <fstream>\nint main(){std::ifstream in("data.in");'
                'std::ofstream out("data.out"); int n; in >> n; out << n; return 0;}\n',
            )
            (samples / "io.json").write_text('{"input":"data.in","output":"data.out"}', encoding="utf-8")
            (samples / "custom_1.in").write_text("6", encoding="utf-8")
            (samples / "custom_1.ans").write_text("6", encoding="utf-8")
            (samples / "custom_2.in").write_text("8", encoding="utf-8")

            report = run_samples(source, samples, case_id="custom_2")

            self.assertEqual(len(report["cases"]), 1)
            self.assertEqual(report["cases"][0]["status"], "NO ANSWER")
            self.assertEqual(report["cases"][0]["output"], "8")
            self.assertFalse((samples / "custom_1.out").exists())


if __name__ == "__main__":
    unittest.main()
