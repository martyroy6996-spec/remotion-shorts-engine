import csv
import tempfile
import unittest
from pathlib import Path

from pipeline.gta6_review import load_candidates


class CandidateLoadingTests(unittest.TestCase):
    def write_csv(self, rows):
        temp = tempfile.TemporaryDirectory()
        path = Path(temp.name) / "candidates.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["start", "end", "score", "transcript"]
            )
            writer.writeheader()
            writer.writerows(rows)
        self.addCleanup(temp.cleanup)
        return path

    def test_candidates_are_sorted_by_score_descending(self):
        path = self.write_csv([
            {"start": "10", "end": "40", "score": "3", "transcript": "low"},
            {"start": "50", "end": "80", "score": "9", "transcript": "high"},
        ])
        result = load_candidates(path, 2)
        self.assertEqual(result[0]["transcript"], "high")
        self.assertEqual(result[1]["transcript"], "low")

    def test_limit_is_respected(self):
        path = self.write_csv([
            {"start": "10", "end": "40", "score": "3", "transcript": "a"},
            {"start": "50", "end": "80", "score": "9", "transcript": "b"},
        ])
        self.assertEqual(len(load_candidates(path, 1)), 1)

    def test_empty_candidate_file_fails_loudly(self):
        path = self.write_csv([])
        with self.assertRaises(ValueError):
            load_candidates(path, 10)

    def test_invalid_numeric_timecode_fails_loudly(self):
        path = self.write_csv([
            {"start": "not-a-time", "end": "40", "score": "3", "transcript": "bad"},
        ])
        with self.assertRaises(ValueError):
            load_candidates(path, 10)


if __name__ == "__main__":
    unittest.main()
