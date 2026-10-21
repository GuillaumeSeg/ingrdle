import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rich.console import Console

from scripts.review_batch import review_batch


class ReviewBatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.batch_path = self.directory / "batch_2026-10-20.json"
        self.output_path = self.directory / "batch_2026-10-20_validated.json"
        self.document = {
            "date": "2026-10-20",
            "seed": 123,
            "questions": [self.make_question("A"), self.make_question("B")],
        }
        self.batch_path.write_text(json.dumps(self.document), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @staticmethod
    def make_question(name: str) -> dict[str, object]:
        return {
            "product_code": name,
            "product_name": f"Product {name}",
            "brands": "Brand",
            "image_url": "https://example.com/image.jpg",
            "ingredients": ["Salt", "Sugar"],
            "hidden_ingredient_index": 1,
            "hidden_ingredient": "Sugar",
            "choices": ["Salt", "Sugar"],
        }

    def test_skip_requeues_question_and_output_contains_kept_questions(self) -> None:
        console = Console(file=None, force_terminal=False, width=100)
        with patch("builtins.input", side_effect=["s", "k", "r"]):
            result = review_batch(self.batch_path, self.output_path, console)

        self.assertEqual(result, self.output_path)
        validated = json.loads(self.output_path.read_text(encoding="utf-8"))
        self.assertEqual(validated["date"], self.document["date"])
        self.assertEqual(validated["seed"], self.document["seed"])
        self.assertEqual(
            [question["product_code"] for question in validated["questions"]],
            ["B"],
        )
        self.assertEqual(json.loads(self.batch_path.read_text()), self.document)

    def test_quit_does_not_write_output(self) -> None:
        console = Console(file=None, force_terminal=False, width=100)
        with patch("builtins.input", return_value="q"):
            result = review_batch(self.batch_path, self.output_path, console)

        self.assertIsNone(result)
        self.assertFalse(self.output_path.exists())


if __name__ == "__main__":
    unittest.main()
