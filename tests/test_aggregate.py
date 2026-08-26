import json
import shutil
import tempfile
import unittest
from pathlib import Path

from hunyuanocr_bench.aggregate import aggregate_results


ROOT = Path(__file__).resolve().parents[1]
PUBLISHED_IDS = [
    "nvidia-rtx4090-amd-sys-741ge-tnrt",
    "amd-w7900d-gpu1-xw-k8s-test-m-001",
    "nvidia-gb10-spark2-shanghai",
]
SAMPLED_ID = "amd-strix-halo-halo3"


class AggregateTests(unittest.TestCase):
    def _copy_machine_result(self, root: Path, machine_id: str) -> None:
        machine_dir = root / "machines"
        machine_dir.mkdir(exist_ok=True)
        shutil.copy2(
            ROOT / "machines" / f"{machine_id}.json",
            machine_dir / f"{machine_id}.json",
        )
        shutil.copytree(
            ROOT / "results" / machine_id,
            root / "results" / machine_id,
        )

    def test_speed_only_results_and_sampled_reference_are_separated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for machine_id in PUBLISHED_IDS + [SAMPLED_ID]:
                self._copy_machine_result(root, machine_id)
            output_dir = root / "leaderboards"
            self.assertEqual(aggregate_results(root / "results", output_dir), [])

            speed_results = json.loads(
                (output_dir / "speed-results.json").read_text(encoding="utf-8")
            )
            published = [result for result in speed_results if result["publishable"]]
            sampled = [result for result in speed_results if not result["publishable"]]
            self.assertEqual([result["machine_id"] for result in published], PUBLISHED_IDS)
            self.assertEqual([result["speed"]["profile_id"] for result in published], ["quick9-c1"] * 3)
            self.assertEqual([result["machine_id"] for result in sampled], [SAMPLED_ID])
            self.assertEqual(sampled[0]["speed"]["profile_id"], "sampled-30-from-584")

            leaderboard = (output_dir / "speed.md").read_text(encoding="utf-8")
            self.assertIn("## Published Speed Results", leaderboard)
            self.assertIn("## Non-comparable References", leaderboard)
            positions = [leaderboard.index(machine_id) for machine_id in PUBLISHED_IDS]
            self.assertEqual(positions, sorted(positions))
            self.assertLess(leaderboard.index(PUBLISHED_IDS[-1]), leaderboard.index(SAMPLED_ID))

            overview = (root / "results" / "README.md").read_text(encoding="utf-8")
            self.assertIn("# Results Overview", overview)
            self.assertIn("## Speed Results", overview)
            self.assertNotIn("## Published Speed Results", overview)
            self.assertNotIn("## Non-comparable Sampled References", overview)
            self.assertIn("No complete accuracy result has been published yet", overview)
            self.assertIn("[Speed leaderboard](../leaderboards/speed.md)", overview)
            self.assertIn("[Structured speed results](../leaderboards/speed-results.json)", overview)
            overview_ids = PUBLISHED_IDS + [SAMPLED_ID]
            overview_positions = [overview.index(machine_id) for machine_id in overview_ids]
            self.assertEqual(overview_positions, sorted(overview_positions))
            for machine_id in overview_ids:
                self.assertIn(f"[{machine_id}]({machine_id}/)", overview)
            self.assertEqual(overview.count("| Machine | Accelerator | Profile |"), 1)
            self.assertNotIn("not ranked against the table above", overview)

    def test_tampered_speed_summary_is_rejected(self) -> None:
        machine_id = PUBLISHED_IDS[0]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._copy_machine_result(root, machine_id)
            destination = root / "results" / machine_id
            speed_path = next(destination.glob("*/speed.json"))
            speed = json.loads(speed_path.read_text(encoding="utf-8"))
            speed["page_per_second"] = 999
            speed_path.write_text(json.dumps(speed), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "does not match request records"):
                aggregate_results(root / "results", root / "leaderboards")


if __name__ == "__main__":
    unittest.main()
