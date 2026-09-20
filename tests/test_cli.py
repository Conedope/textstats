"""End-to-end CLI tests via subprocess."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CORPUS = (
    "The quick brown fox jumps over the lazy dog. "
    "Pack my box with five dozen liquor jugs. "
    "The rainbow is lovely and bright. "
    "How vexingly quick daft zebras jump."
)


def run_cli(args, input_text=None):
    return subprocess.run(
        [sys.executable, "-m", "textstats.cli", *args],
        cwd=str(ROOT),
        input=input_text,
        capture_output=True,
        text=True,
    )


class CliBlockTest(unittest.TestCase):
    def test_block_contains_sections_and_key_numbers(self):
        proc = run_cli(["-"], input_text=CORPUS)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout
        for token in (
            "Counts",
            "sentences",
            "words",
            "unique",
            "Averages",
            "Word length histogram",
            "Sentence length histogram",
            "Readability",
            "Flesch Reading Ease",
            "Flesch-Kincaid Grade",
            "Gunning Fog",
            "SMOG",
        ):
            self.assertIn(token, out)
        self.assertIn("words      : 29", out)
        self.assertIn("sentences  : 4", out)

    def test_readability_section_rounds_to_two_decimals(self):
        proc = run_cli(["-"], input_text=CORPUS)
        self.assertIn("Flesch Reading Ease : 85.70", proc.stdout)
        self.assertIn("Flesch-Kincaid Grade: 3.11", proc.stdout)
        self.assertIn("Gunning Fog         : 2.93", proc.stdout)
        self.assertIn("SMOG                : 7.17", proc.stdout)

    def test_no_histograms_flag(self):
        proc = run_cli(["--no-histograms", "-"], input_text=CORPUS)
        self.assertNotIn("Word length histogram", proc.stdout)
        self.assertNotIn("Sentence length histogram", proc.stdout)
        self.assertIn("Readability", proc.stdout)

    def test_file_argument_matches_stdin(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
            fh.write(CORPUS)
            path = fh.name
        try:
            proc_file = run_cli([path])
            self.assertEqual(proc_file.returncode, 0, proc_file.stderr)
            self.assertIn("words      : 29", proc_file.stdout)
            self.assertIn("Source: %s" % path, proc_file.stdout)
        finally:
            os.unlink(path)

    def test_missing_file_exits_2(self):
        proc = run_cli(["/nonexistent/textstats-no-such-file.txt"])
        self.assertEqual(proc.returncode, 2)
        self.assertIn("textstats: error", proc.stderr)

    def test_empty_stdin_is_not_an_error(self):
        proc = run_cli(["-"], input_text="")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Readability", proc.stdout)
        self.assertIn("words      : 0", proc.stdout)

    def test_read_from_pipe_when_no_file_given(self):
        proc = run_cli([], input_text="Only one sentence here.")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Source: <stdin>", proc.stdout)
        self.assertIn("sentences  : 1", proc.stdout)


class CliJsonTest(unittest.TestCase):
    def parse(self, proc):
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_json_parses_and_counts_match(self):
        data = self.parse(run_cli(["--json", "-"], input_text=CORPUS))
        self.assertEqual(data["words"], 29)
        self.assertEqual(data["sentences"], 4)
        self.assertEqual(data["paragraphs"], 1)
        self.assertEqual(data["unique_words"], 26)
        self.assertEqual(sum(data["word_length_hist"].values()), 29)
        self.assertEqual(sum(data["sentence_length_hist"].values()), 4)

    def test_json_floats_rounded_to_two_decimals(self):
        data = self.parse(run_cli(["--json", "-"], input_text=CORPUS))
        for value in data.values():
            if isinstance(value, float):
                self.assertTrue(round(value, 2) == value, "expected 2-decimal float, got %r" % value)
        self.assertEqual(data["flesch"], 85.7)
        self.assertEqual(data["flesch_kincaid"], 3.11)
        self.assertEqual(data["gunning_fog"], 2.93)
        self.assertEqual(data["smog"], 7.17)
        self.assertEqual(data["avg_sentence_length"], 7.25)
        self.assertAlmostEqual(data["avg_word_length"], 4.28, places=2)
        self.assertAlmostEqual(data["unique_ratio"], 0.9, places=2)

    def test_json_empty_input(self):
        data = self.parse(run_cli(["--json", "-"], input_text=""))
        self.assertEqual(data["words"], 0)
        self.assertEqual(data["flesch"], 205.82)
        self.assertEqual(data["flesch_kincaid"], -15.2)
        self.assertEqual(data["word_length_hist"], {str(n): 0 for n in range(1, 13)})


class CliVersionTest(unittest.TestCase):
    def test_version(self):
        proc = run_cli(["--version"])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("textstats 1.0.0", proc.stdout)

    def test_help(self):
        proc = run_cli(["--help"])
        self.assertEqual(proc.returncode, 0)
        for token in ("--json", "--no-histograms", "--version", "FILE"):
            self.assertIn(token, proc.stdout)


class CliModuleRunTest(unittest.TestCase):
    def test_python_dash_m_textstats(self):
        proc = subprocess.run(
            [sys.executable, "-m", "textstats", "--version"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("textstats 1.0.0", proc.stdout)


if __name__ == "__main__":
    unittest.main()