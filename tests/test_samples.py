import tempfile
import unittest
from pathlib import Path

from CompetitiveHelper.cph_samples import add_case, case_ids, pair_files, preview


class SampleTests(unittest.TestCase):
    def test_batch_uses_names_and_single_pair_accepts_different_names(self):
        self.assertEqual(
            pair_files(["a.in", "b.in"], ["b.out", "a.ans"]),
            [("a.in", "a.ans"), ("b.in", "b.out")]
        )
        self.assertEqual(pair_files(["chosen.in"], ["answer.txt"]), [("chosen.in", "answer.txt")])
        with self.assertRaises(ValueError):
            pair_files(["a.in", "b.in"], ["a.ans", "c.ans"])

    def test_import_preserves_bytes_and_allocates_unique_pairs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_path, answer_path = root / "source.in", root / "source.out"
            input_path.write_bytes(b"1 2\r\n")
            answer_path.write_bytes(b"3\n")
            directory = root / "samples"
            blank = add_case(str(directory))
            imported = add_case(str(directory), str(input_path), str(answer_path))
            self.assertEqual(case_ids(str(directory)), [blank, imported])
            self.assertEqual((directory / (blank + ".ans")).read_bytes(), b"")
            self.assertEqual((directory / (imported + ".in")).read_bytes(), b"1 2\r\n")
            self.assertEqual((directory / (imported + ".ans")).read_bytes(), b"3\n")
            self.assertEqual(preview(str(directory / (imported + ".out"))), (None, False))

    def test_preview_is_bounded_by_lines_and_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "large.in"
            path.write_bytes(b"one\ntwo\nthree\n")
            self.assertEqual(preview(str(path), limit=7, max_lines=1), ("one", True))
            self.assertEqual(preview(str(path)), ("one\ntwo\nthree", False))
