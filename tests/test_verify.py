import json
import tempfile
import unittest
from pathlib import Path

from hunyuanocr_bench.verify import verify_predictions


class PredictionVerificationTests(unittest.TestCase):
    def test_complete_prediction_set_allows_empty_model_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            gt = root / "gt.json"
            gt.write_text(json.dumps([
                {"page_info": {"image_path": "a.png"}},
                {"page_info": {"image_path": "b.jpg"}},
            ]))
            predictions = root / "predictions"
            predictions.mkdir()
            (predictions / "a.md").write_text("")
            (predictions / "b.md").write_text("content")
            (predictions / "results.jsonl").write_text(
                json.dumps({"image": "a.png", "ok": True}) + "\n"
                + json.dumps({"image": "b.jpg", "ok": True}) + "\n"
            )

            report = verify_predictions(gt, predictions)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["zero_byte_count"], 1)

    def test_failed_prediction_record_fails_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            gt = root / "gt.json"
            gt.write_text(json.dumps([{"page_info": {"image_path": "a.png"}}]))
            predictions = root / "predictions"
            predictions.mkdir()
            (predictions / "a.md").write_text("partial")
            (predictions / "results.jsonl").write_text(
                json.dumps({"image": "a.png", "ok": False, "error": "boom"}) + "\n"
            )

            report = verify_predictions(gt, predictions)
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["failed_record_count"], 1)


if __name__ == "__main__":
    unittest.main()
