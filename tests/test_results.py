import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hunyuanocr_bench.config import sha256_file, sha256_lines
from hunyuanocr_bench.results import assemble_result, load_and_validate_result
from hunyuanocr_bench.speed import summarize_speed


class PublishedResultTests(unittest.TestCase):
    def _write_fixture(self, root: Path) -> Path:
        machine = {
            "machine_id": "amd-test-gpu",
            "vendor": "amd",
            "accelerator": {"model": "Test GPU", "count": 1, "memory_gib_each": 48},
            "runtime": {
                "framework": "vLLM",
                "framework_version": "1.0",
                "inference_method": "ar",
                "base_url": "http://127.0.0.1:8000/v1",
                "served_model_name": "tencent/HunyuanOCR",
                "container_image": "example/image:test",
                "container_image_digest": "sha256:test",
                "precision": "bfloat16",
                "tensor_parallel": 1
            },
            "software": {"os": "Linux", "driver": "x", "compute_stack": "ROCm", "pytorch": "x"}
        }
        metrics = {
            "overall": 94.75666666666666,
            "text_edit": 0.039,
            "formula_cdm": 94.5,
            "table_teds": 93.67,
            "table_teds_s": 94.71,
            "order_edit": 0.129
        }
        evaluator = {
            "runtime_environment": {"system": {"python_version": "3.10"}},
            "stage_execution": {"page_match": {"page_count": 1651}},
            "page_denominators": {
                "display_formula": {"CDM": {"ALL": 313}},
                "table": {"TEDS": {"ALL": 458}}
            },
            "benchmark_provenance": {
                "protocol_id": "hunyuanocr-1.5-omnidocbench-1.6-v1",
                "dataset_revision": "d386947f7fc3bafdcd756c8485845a2f43a19875",
                "dataset_pages": 1651,
                "gt_sha256": "a45cd84b04ad8b793e775089640e6b681209abea33ead54c1828ddca35fae496",
                "evaluator_revision": "147cd5ac9472002f5751221d390bf00abdbc0d2f",
                "evaluator_image": "ghcr.io/zeng-weijun/omnidocbench-eval@sha256:6116ad72172e763b5c43e963d5efebf2093f2362b975f58156ce4f6c9142e617",
                "config_sha256": "9ecdab12fa28c51cfcbac74cc9d701f8114b92fe628829453298a4c5693d5381"
            },
            "notebook_metric_summary": {
                "overall_notebook": metrics["overall"],
                "metrics": {
                    "text_block_Edit_dist": {"notebook_value": metrics["text_edit"]},
                    "display_formula_CDM": {"notebook_value": metrics["formula_cdm"]},
                    "table_TEDS": {"notebook_value": metrics["table_teds"]},
                    "table_TEDS_structure_only": {"notebook_value": metrics["table_teds_s"]},
                    "reading_order_Edit_dist": {"notebook_value": metrics["order_edit"]}
                }
            }
        }
        (root / "evaluator-summary.json").write_text(json.dumps(evaluator, indent=2) + "\n")
        accuracy = {
            "status": "PASS",
            "protocol_id": "hunyuanocr-1.5-omnidocbench-1.6-v1",
            "dataset_pages": 1651,
            "metrics": metrics,
            "source": {"sha256": sha256_file(root / "evaluator-summary.json")}
        }
        inventory = (
            Path(__file__).resolve().parents[1] / "protocol" / "omnidocbench-v1.6-speed-quick9.txt"
        ).read_text(encoding="utf-8").splitlines()
        records = [
            {
                "repetition": repetition,
                "image": image,
                "ok": True,
                "latency_seconds": 2.0,
                "completion_tokens": 10,
                "output_chars": 20,
                "finish_reason": "stop"
            }
            for repetition in range(1, 4)
            for image in inventory
        ]
        parameters = {
            "temperature": 0.0,
            "max_tokens": 8000,
            "extra_body": {"top_k": 1},
            "base_url": "http://127.0.0.1:8000/v1",
            "model": "tencent/HunyuanOCR",
            "concurrency": 1,
            "warmup_pages": 9,
            "repetitions": 3,
            "image_data_url_mime": "image/png"
        }
        speed = summarize_speed(
            records,
            wall_seconds=54.0,
            protocol_id="hunyuanocr-1.5-omnidocbench-1.6-v1",
            profile_id="quick9-c1",
            sample_sha256=sha256_lines(inventory),
            parameters=parameters
        )
        payloads = {
            "machine.json": machine,
            "machine-capture.json": {
                "declared_profile": machine,
                "commands": {"rocm_smi": {"available": True, "returncode": 0}}
            },
            "accuracy.json": accuracy,
            "speed.json": speed,
            "assets-verification.json": {
                "status": "PASS",
                "source_revisions": {
                    "hunyuanocr": "c55965d3da1e6f41987abec8068f2e70851318bc",
                    "omnidocbench": "147cd5ac9472002f5751221d390bf00abdbc0d2f"
                },
                "source_dirty": {"hunyuanocr": False, "omnidocbench": False},
                "model": {"snapshot": {"verified_files": 22}},
                "dataset": {
                    "revision": "d386947f7fc3bafdcd756c8485845a2f43a19875",
                    "gt_sha256": "a45cd84b04ad8b793e775089640e6b681209abea33ead54c1828ddca35fae496",
                    "pages": 1651,
                    "images": 1651,
                    "subsets": {
                        "v1.5": 1355,
                        "equation_hard": 100,
                        "layout_hard": 99,
                        "table_hard": 97
                    },
                    "snapshot": {"verified_files": 1659}
                }
            },
            "prediction-verification.json": {
                "status": "PASS",
                "gt_pages": 1651,
                "markdown_files": 1651,
                "latest_records": 1651,
                "missing_markdown_count": 0,
                "extra_markdown_count": 0,
                "missing_record_count": 0,
                "failed_record_count": 0
            }
        }
        for filename, payload in payloads.items():
            (root / filename).write_text(json.dumps(payload, indent=2) + "\n")
        (root / "speed-records.jsonl").write_text(
            "".join(json.dumps(record) + "\n" for record in records)
        )
        artifact_names = {
            "accuracy_sha256": "accuracy.json",
            "speed_sha256": "speed.json",
            "machine_capture_sha256": "machine-capture.json",
            "assets_verification_sha256": "assets-verification.json",
            "prediction_verification_sha256": "prediction-verification.json",
            "evaluator_summary_sha256": "evaluator-summary.json",
            "speed_records_sha256": "speed-records.jsonl",
            "machine_profile_sha256": "machine.json"
        }
        result = {
            "schema_version": "1.0",
            "status": "PASS",
            "run_id": root.name,
            "protocol_id": "hunyuanocr-1.5-omnidocbench-1.6-v1",
            "protocol_revision": "a" * 40,
            "machine_id": machine["machine_id"],
            "vendor": machine["vendor"],
            "accelerator": machine["accelerator"],
            "runtime": machine["runtime"],
            "model": {
                "code_revision": "c55965d3da1e6f41987abec8068f2e70851318bc",
                "weights_revision": "449e7d471a8a1ef5bd5d652e4881183d7252cbc7"
            },
            "dataset": {"revision": "d386947f7fc3bafdcd756c8485845a2f43a19875"},
            "evaluator": {"revision": "147cd5ac9472002f5751221d390bf00abdbc0d2f"},
            "accuracy": accuracy,
            "speed": speed,
            "artifacts": {
                key: sha256_file(root / filename) for key, filename in artifact_names.items()
            }
        }
        result_path = root / "result.json"
        result_path.write_text(json.dumps(result, indent=2) + "\n")
        return result_path

    def test_published_result_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = self._write_fixture(Path(temporary))
            self.assertEqual(load_and_validate_result(result)["status"], "PASS")

    def test_tampered_speed_artifact_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self._write_fixture(root)
            (root / "speed.json").write_text("{}\n")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                load_and_validate_result(result)

    def test_real_assembler_includes_all_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_fixture(root)
            machine = json.loads((root / "machine.json").read_text())
            protocol = {
                "protocol_id": "hunyuanocr-1.5-omnidocbench-1.6-v1",
                "model": {
                    "code_revision": "c55965d3da1e6f41987abec8068f2e70851318bc",
                    "weights_revision": "449e7d471a8a1ef5bd5d652e4881183d7252cbc7"
                },
                "dataset": {"revision": "d386947f7fc3bafdcd756c8485845a2f43a19875"},
                "evaluator": {"revision": "147cd5ac9472002f5751221d390bf00abdbc0d2f"}
            }
            with patch("hunyuanocr_bench.results.git_revision", return_value="a" * 40):
                result = assemble_result(
                    root, root.name, machine, protocol,
                    root / "accuracy.json", root / "speed.json",
                    root / "machine-capture.json", root / "assets-verification.json",
                    root / "prediction-verification.json", root / "evaluator-summary.json",
                    root / "speed-records.jsonl", root / "machine.json"
                )
            self.assertEqual(result["dataset"], protocol["dataset"])
            self.assertEqual(result["evaluator"], protocol["evaluator"])
            self.assertEqual(len(result["artifacts"]), 8)


if __name__ == "__main__":
    unittest.main()
