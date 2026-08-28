import json
import shutil
import tempfile
import unittest
from pathlib import Path

from hunyuanocr_bench.aggregate import aggregate_results
from hunyuanocr_bench.config import load_protocol


ROOT = Path(__file__).resolve().parents[1]
PUBLISHED_IDS = [
    "nvidia-rtx4090-amd-sys-741ge-tnrt",
    "amd-w7900d-gpu1-xw-k8s-test-m-001",
    "amd-strix-halo-halo3",
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
            for machine_id in dict.fromkeys(PUBLISHED_IDS + [SAMPLED_ID]):
                self._copy_machine_result(root, machine_id)
            for local_accuracy in (root / "results").glob(
                "*/local-evaluator-accuracy-*"
            ):
                shutil.rmtree(local_accuracy)
            output_dir = root / "leaderboards"
            results = aggregate_results(root / "results", output_dir)
            self.assertEqual(
                [result["machine_id"] for result in results],
                ["amd-w7900d-gpu1-xw-k8s-test-m-001"],
            )

            speed_results = json.loads(
                (output_dir / "speed-results.json").read_text(encoding="utf-8")
            )
            published = [result for result in speed_results if result["publishable"]]
            sampled = [result for result in speed_results if not result["publishable"]]
            self.assertEqual([result["machine_id"] for result in published], PUBLISHED_IDS)
            self.assertEqual(
                [result["speed"]["profile_id"] for result in published],
                ["quick9-c1"] * len(PUBLISHED_IDS),
            )
            self.assertEqual([result["machine_id"] for result in sampled], [SAMPLED_ID])
            self.assertEqual(sampled[0]["speed"]["profile_id"], "sampled-30-from-584")

            leaderboard = (output_dir / "speed.md").read_text(encoding="utf-8")
            self.assertIn("## Published Speed Results", leaderboard)
            self.assertIn("## Non-comparable References", leaderboard)
            positions = [leaderboard.index(machine_id) for machine_id in PUBLISHED_IDS]
            self.assertEqual(positions, sorted(positions))
            self.assertEqual(leaderboard.count(f"| {SAMPLED_ID} |"), 2)
            self.assertLess(leaderboard.index(PUBLISHED_IDS[-1]), leaderboard.rindex(SAMPLED_ID))

            overview = (root / "results" / "README.md").read_text(encoding="utf-8")
            self.assertIn("# Results Overview", overview)
            self.assertIn("## Speed Results", overview)
            self.assertNotIn("## Published Speed Results", overview)
            self.assertNotIn("## Non-comparable Sampled References", overview)
            self.assertIn("1 canonical accuracy result(s)", overview)
            self.assertIn("Overall 95.593058", overview)
            self.assertIn("[Speed leaderboard](../leaderboards/speed.md)", overview)
            self.assertIn("[Structured speed results](../leaderboards/speed-results.json)", overview)
            overview_ids = PUBLISHED_IDS + [SAMPLED_ID]
            overview_rows = [
                line.split("](", 1)[0].removeprefix("| [")
                for line in overview.splitlines()
                if line.startswith("| [")
            ]
            self.assertEqual(overview_rows, overview_ids)
            for machine_id in dict.fromkeys(overview_ids):
                self.assertIn(f"[{machine_id}]({machine_id}/)", overview)
            self.assertEqual(overview.count("| Machine | Accelerator | Profile |"), 1)
            self.assertNotIn("not ranked against the table above", overview)

    def test_canonical_and_local_accuracy_are_labeled_separately(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._copy_machine_result(root, "amd-r9700-workstation-sh")
            self._copy_machine_result(root, "nvidia-rtx4090-amd-sys-741ge-tnrt")

            results = aggregate_results(root / "results", root / "leaderboards")

            self.assertEqual(
                [result["machine_id"] for result in results],
                ["amd-r9700-workstation-sh"],
            )
            accuracy = (root / "leaderboards" / "accuracy.md").read_text(encoding="utf-8")
            self.assertIn("amd-r9700-workstation-sh", accuracy)
            self.assertNotIn("nvidia-rtx4090-amd-sys-741ge-tnrt", accuracy)
            overview = (root / "results" / "README.md").read_text(encoding="utf-8")
            self.assertIn("1 canonical accuracy result(s)", overview)
            self.assertIn("1 complete local-evaluator result(s)", overview)
            self.assertIn("Overall 95.618309", overview)
            self.assertIn("Overall 95.443681 (non-canonical evaluator runtime)", overview)

    def test_tampered_local_accuracy_artifact_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            machine_id = "nvidia-rtx4090-amd-sys-741ge-tnrt"
            self._copy_machine_result(root, machine_id)
            accuracy_path = next(
                (root / "results" / machine_id).glob("local-evaluator-accuracy-*/accuracy.json")
            )
            accuracy = json.loads(accuracy_path.read_text(encoding="utf-8"))
            accuracy["metrics"]["overall"] = 99
            accuracy_path.write_text(json.dumps(accuracy), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "artifact SHA-256 mismatch"):
                aggregate_results(root / "results", root / "leaderboards")

    def test_root_accuracy_comparison_matches_evidence(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        protocol = load_protocol()
        rtx_accuracy = next(
            (ROOT / "results" / "nvidia-rtx4090-amd-sys-741ge-tnrt").glob(
                "local-evaluator-accuracy-*/accuracy.json"
            )
        )
        w7900_accuracy = next(
            (ROOT / "results" / "amd-w7900d-gpu1-xw-k8s-test-m-001").glob(
                "*/accuracy.json"
            )
        )
        r9700_accuracy = next(
            (ROOT / "results" / "amd-r9700-workstation-sh").glob("*/accuracy.json")
        )
        sources = [
            protocol["paper_reference"]["accuracy"],
            json.loads(rtx_accuracy.read_text(encoding="utf-8"))["metrics"],
            json.loads(w7900_accuracy.read_text(encoding="utf-8"))["metrics"],
            json.loads(r9700_accuracy.read_text(encoding="utf-8"))["metrics"],
        ]
        rows = {
            "Overall↑": ("overall", (2, 6, 6, 6)),
            "TextEdit↓": ("text_edit", (3, 6, 6, 6)),
            "FormulaCDM↑": ("formula_cdm", (2, 6, 6, 6)),
            "TableTEDS↑": ("table_teds", (2, 6, 6, 6)),
            "TableTEDS_S↑": ("table_teds_s", (2, 6, 6, 6)),
            "OrderEdit↓": ("order_edit", (3, 6, 6, 6)),
        }
        for label, (key, digits) in rows.items():
            values = [f"{source[key]:.{places}f}" for source, places in zip(sources, digits)]
            self.assertIn(f"| {label} | {' | '.join(values)} |", readme)
        self.assertIn("results/nvidia-rtx4090-amd-sys-741ge-tnrt/SERVING.md", readme)
        self.assertIn(
            "results/amd-w7900d-gpu1-xw-k8s-test-m-001/SERVING.md", readme
        )
        self.assertIn("results/amd-strix-halo-halo3/SERVING.md", readme)
        self.assertIn("results/amd-r9700-workstation-sh/SERVING.md", readme)

        w7900_speed = json.loads(
            next(
                (ROOT / "results" / "amd-w7900d-gpu1-xw-k8s-test-m-001").glob(
                    "*/speed.json"
                )
            ).read_text(encoding="utf-8")
        )
        self.assertIn(
            "| [AMD Radeon PRO W7900D]"
            "(results/amd-w7900d-gpu1-xw-k8s-test-m-001/SERVING.md) | "
            f"{w7900_speed['average_latency_seconds']:.3f} | "
            f"{w7900_speed['latency_seconds']['p95']:.3f} | "
            f"{w7900_speed['page_per_second']:.4f} | "
            f"{w7900_speed['token_per_second']:.1f} |",
            readme,
        )

        halo_speed = json.loads(
            (
                ROOT
                / "results/amd-strix-halo-halo3/interim-speed-quick9-c1/speed.json"
            ).read_text(encoding="utf-8")
        )
        self.assertIn(
            "| [AMD Ryzen AI Max+ 395 (Radeon 8060S)]"
            "(results/amd-strix-halo-halo3/SERVING.md) | "
            f"{halo_speed['average_latency_seconds']:.3f} | "
            f"{halo_speed['latency_seconds']['p95']:.3f} | "
            f"{halo_speed['page_per_second']:.4f} | "
            f"{halo_speed['token_per_second']:.1f} |",
            readme,
        )

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
