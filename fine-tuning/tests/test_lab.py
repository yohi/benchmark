import unittest
from pathlib import Path
from lab import validate, evaluate

F = Path(__file__).resolve().parents[1] / "fixtures"

class LabTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate([F / f"{s}.jsonl" for s in ("train", "dev", "test")])["status"], "VALIDATED")

    def test_overlap(self):
        with self.assertRaises(ValueError):
            validate([F / "train.jsonl", F / "train.jsonl"])

    def test_evaluate(self):
        self.assertEqual(evaluate(F / "test.jsonl", F / "predictions.jsonl")["accuracy"], 1.0)

    def test_missing_prediction(self):
        with self.assertRaises(ValueError):
            evaluate(F / "dev.jsonl", F / "predictions.jsonl")
