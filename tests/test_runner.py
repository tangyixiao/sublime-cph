import tempfile
import unittest
from pathlib import Path

from CompetitiveHelper.cph_runner import run_samples


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


if __name__ == "__main__":
    unittest.main()
