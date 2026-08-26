from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .accuracy import extract_metric_result, extract_run_summary
from .config import load_json, load_machine, sha256_file, sha256_lines
from .metrics import component_overall
from .speed import summarize_speed


MACHINE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
GIT_REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def git_revision(root: Path) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "kickoff"],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def validate_result(result: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if result.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")
    if result.get("protocol_id") != "hunyuanocr-1.5-omnidocbench-1.6-v1":
        errors.append("unexpected protocol_id")
    if not GIT_REVISION_PATTERN.fullmatch(result.get("protocol_revision") or ""):
        errors.append("protocol_revision must be the committed kickoff SHA")
    if not result.get("run_id"):
        errors.append("run_id is required")

    machine_id = result.get("machine_id", "")
    if not MACHINE_ID_PATTERN.fullmatch(machine_id):
        errors.append("invalid machine_id")
    vendor = result.get("vendor")
    if vendor not in {"amd", "nvidia"} or not machine_id.startswith(f"{vendor}-"):
        errors.append("machine_id and vendor are inconsistent")
    if result.get("status") != "PASS":
        errors.append("result status must be PASS")

    model = result.get("model") or {}
    dataset = result.get("dataset") or {}
    evaluator = result.get("evaluator") or {}
    if model.get("code_revision") != "c55965d3da1e6f41987abec8068f2e70851318bc":
        errors.append("model code revision mismatch")
    if model.get("weights_revision") != "449e7d471a8a1ef5bd5d652e4881183d7252cbc7":
        errors.append("model weights revision mismatch")
    if dataset.get("revision") != "d386947f7fc3bafdcd756c8485845a2f43a19875":
        errors.append("dataset revision mismatch")
    if evaluator.get("revision") != "147cd5ac9472002f5751221d390bf00abdbc0d2f":
        errors.append("evaluator revision mismatch")

    accuracy = result.get("accuracy") or {}
    speed = result.get("speed") or {}
    if accuracy.get("status") != "PASS":
        errors.append("accuracy status must be PASS")
    if accuracy.get("protocol_id") != result.get("protocol_id"):
        errors.append("accuracy protocol_id mismatch")
    if accuracy.get("dataset_pages") != 1651:
        errors.append("accuracy must cover all 1651 pages")
    required_metrics = {"overall", "text_edit", "formula_cdm", "table_teds", "table_teds_s", "order_edit"}
    metrics = accuracy.get("metrics") or {}
    if set(metrics.keys()) != required_metrics:
        errors.append("accuracy metrics do not match the canonical six columns")
    for name, lower, upper in (
        ("overall", 0.0, 100.0),
        ("text_edit", 0.0, 1.0),
        ("formula_cdm", 0.0, 100.0),
        ("table_teds", 0.0, 100.0),
        ("table_teds_s", 0.0, 100.0),
        ("order_edit", 0.0, 1.0),
    ):
        value = metrics.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not lower <= value <= upper:
            errors.append(f"accuracy metric {name} is out of range")
    if all(isinstance(metrics.get(key), (int, float)) for key in ("text_edit", "formula_cdm", "table_teds")):
        derived_overall = component_overall(
            metrics["text_edit"], metrics["formula_cdm"], metrics["table_teds"]
        )
        if abs(metrics.get("overall", -1) - derived_overall) > 0.03:
            errors.append("accuracy Overall does not match official formula")

    if speed.get("status") != "PASS":
        errors.append("speed status must be PASS")
    profile_id = speed.get("profile_id")
    if profile_id not in {"full1651-c1", "paper930-c1"}:
        errors.append("unknown speed profile_id")
    if profile_id != "full1651-c1":
        errors.append("paper930-c1 is not publishable until its official inventory is released")
    expected_speed_pages = {"full1651-c1": 1651, "paper930-c1": 930}.get(profile_id)
    if speed.get("images") != expected_speed_pages or speed.get("successful") != speed.get("requests"):
        errors.append("speed page/request inventory is incomplete")
    if profile_id == "full1651-c1" and speed.get("sample_inventory_sha256") != (
        "344d236b31d265915b723f3106613bbbeaf37cf988db7f58b76d88cbb7c2a1b4"
    ):
        errors.append("full1651 speed inventory hash mismatch")
    if speed.get("failed") != 0:
        errors.append("speed contains failed requests")
    if speed.get("missing_completion_tokens") != 0:
        errors.append("speed contains responses without completion token counts")
    if speed.get("requests") != expected_speed_pages:
        errors.append("speed must run exactly one request per profile page")
    parameters = speed.get("parameters") or {}
    if parameters.get("concurrency") != 1:
        errors.append("speed concurrency must be 1")
    if parameters.get("temperature") != 0.0 or parameters.get("max_tokens") != 8000:
        errors.append("speed request parameters do not match protocol")
    if (parameters.get("extra_body") or {}).get("top_k") != 1:
        errors.append("speed top_k must be 1")
    expected_warmup = {"full1651-c1": 10, "paper930-c1": 0}.get(profile_id)
    if parameters.get("warmup_pages") != expected_warmup or parameters.get("repetitions") != 1:
        errors.append("speed warm-up or repetition count does not match profile")
    if parameters.get("image_data_url_mime") != "image/png":
        errors.append("speed image data URL MIME must match the paper")
    average_latency = speed.get("average_latency_seconds")
    page_per_second = speed.get("page_per_second")
    if isinstance(average_latency, bool) or not isinstance(average_latency, (int, float)) or average_latency <= 0:
        errors.append("speed average latency must be positive")
    if isinstance(page_per_second, bool) or not isinstance(page_per_second, (int, float)) or page_per_second <= 0:
        errors.append("speed page_per_second must be positive")
    elif isinstance(average_latency, (int, float)) and abs(page_per_second * average_latency - 1.0) > 0.001:
        errors.append("speed latency and page/s are inconsistent for concurrency 1")
    return errors


def assemble_result(
    root: Path,
    run_id: str,
    machine: dict[str, Any],
    protocol: dict[str, Any],
    accuracy_path: Path,
    speed_path: Path,
    machine_capture_path: Path | None = None,
    assets_verification_path: Path | None = None,
    prediction_verification_path: Path | None = None,
    evaluator_summary_path: Path | None = None,
    speed_records_path: Path | None = None,
    machine_profile_path: Path | None = None,
) -> dict[str, Any]:
    accuracy = load_json(accuracy_path)
    speed = load_json(speed_path)
    result = {
        "schema_version": "1.0",
        "status": "PASS" if accuracy.get("status") == speed.get("status") == "PASS" else "FAIL",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "protocol_id": protocol["protocol_id"],
        "protocol_revision": git_revision(root),
        "machine_id": machine["machine_id"],
        "vendor": machine["vendor"],
        "accelerator": machine["accelerator"],
        "runtime": machine["runtime"],
        "model": protocol["model"],
        "dataset": protocol["dataset"],
        "evaluator": protocol["evaluator"],
        "accuracy": accuracy,
        "speed": speed,
        "artifacts": {
            "accuracy_sha256": sha256_file(accuracy_path),
            "speed_sha256": sha256_file(speed_path),
        },
    }
    optional_artifacts = {
        "machine_capture_sha256": machine_capture_path,
        "assets_verification_sha256": assets_verification_path,
        "prediction_verification_sha256": prediction_verification_path,
        "evaluator_summary_sha256": evaluator_summary_path,
        "speed_records_sha256": speed_records_path,
        "machine_profile_sha256": machine_profile_path,
    }
    for key, artifact_path in optional_artifacts.items():
        if artifact_path:
            result["artifacts"][key] = sha256_file(artifact_path)
    errors = validate_result(result)
    if errors:
        raise ValueError("invalid assembled result: " + "; ".join(errors))
    return result


def load_and_validate_result(path: Path) -> dict[str, Any]:
    result = load_json(path)
    errors = validate_result(result)
    artifact_files = {
        "accuracy_sha256": "accuracy.json",
        "speed_sha256": "speed.json",
        "machine_capture_sha256": "machine-capture.json",
        "assets_verification_sha256": "assets-verification.json",
        "prediction_verification_sha256": "prediction-verification.json",
        "evaluator_summary_sha256": "evaluator-summary.json",
        "speed_records_sha256": "speed-records.jsonl",
        "machine_profile_sha256": "machine.json",
    }
    artifacts = result.get("artifacts") or {}
    for key, filename in artifact_files.items():
        artifact_path = path.parent / filename
        expected = artifacts.get(key)
        if not artifact_path.is_file() or not expected:
            errors.append(f"required artifact is missing: {filename}")
        elif sha256_file(artifact_path) != expected:
            errors.append(f"artifact SHA-256 mismatch: {filename}")

    if not errors:
        machine = load_machine(path.parent / "machine.json")
        if any(
            machine.get(key) != result.get(key)
            for key in ("machine_id", "vendor", "accelerator", "runtime")
        ):
            errors.append("machine profile does not match canonical result")
        if load_json(path.parent / "accuracy.json") != result.get("accuracy"):
            errors.append("accuracy artifact does not match canonical result")
        speed = load_json(path.parent / "speed.json")
        if speed != result.get("speed"):
            errors.append("speed artifact does not match canonical result")
        for filename in ("assets-verification.json", "prediction-verification.json"):
            if load_json(path.parent / filename).get("status") != "PASS":
                errors.append(f"verification artifact is not PASS: {filename}")
        assets_report = load_json(path.parent / "assets-verification.json")
        if assets_report.get("source_revisions") != {
            "hunyuanocr": "c55965d3da1e6f41987abec8068f2e70851318bc",
            "omnidocbench": "147cd5ac9472002f5751221d390bf00abdbc0d2f",
        }:
            errors.append("asset source revisions do not match protocol")
        if any((assets_report.get("source_dirty") or {}).values()):
            errors.append("asset source checkout was dirty")
        dataset_report = assets_report.get("dataset") or {}
        if dataset_report.get("pages") != 1651 or dataset_report.get("images") != 1651:
            errors.append("asset report does not contain 1651 GT pages/images")
        if dataset_report.get("revision") != "d386947f7fc3bafdcd756c8485845a2f43a19875":
            errors.append("asset dataset revision mismatch")
        if dataset_report.get("gt_sha256") != "a45cd84b04ad8b793e775089640e6b681209abea33ead54c1828ddca35fae496":
            errors.append("asset GT SHA-256 mismatch")
        if (dataset_report.get("snapshot") or {}).get("verified_files") != 1659:
            errors.append("asset dataset snapshot is not fully verified")
        if ((assets_report.get("model") or {}).get("snapshot") or {}).get("verified_files") != 22:
            errors.append("asset model snapshot is not fully verified")
        if dataset_report.get("subsets") != {
            "v1.5": 1355,
            "equation_hard": 100,
            "layout_hard": 99,
            "table_hard": 97,
        }:
            errors.append("asset dataset subset distribution mismatch")

        prediction_report = load_json(path.parent / "prediction-verification.json")
        for key, expected in (
            ("gt_pages", 1651),
            ("markdown_files", 1651),
            ("latest_records", 1651),
            ("missing_markdown_count", 0),
            ("extra_markdown_count", 0),
            ("missing_record_count", 0),
            ("failed_record_count", 0),
        ):
            if prediction_report.get(key) != expected:
                errors.append(f"prediction verification mismatch: {key}")
        capture = load_json(path.parent / "machine-capture.json")
        if capture.get("declared_profile") != machine:
            errors.append("machine capture does not contain the published profile")
        command_key = "rocm_smi" if result["vendor"] == "amd" else "nvidia_smi"
        command_evidence = (capture.get("commands") or {}).get(command_key) or {}
        if not command_evidence.get("available") or command_evidence.get("returncode") != 0:
            errors.append(f"machine capture lacks successful {command_key} evidence")

        evaluator_payload = load_json(path.parent / "evaluator-summary.json")
        required_summary = {
            "runtime_environment", "stage_execution", "page_denominators",
            "notebook_metric_summary", "benchmark_provenance",
        }
        if not required_summary.issubset(evaluator_payload):
            errors.append("evaluator summary is not an official v1.6 run summary")
        provenance = evaluator_payload.get("benchmark_provenance") or {}
        expected_provenance = {
            "protocol_id": "hunyuanocr-1.5-omnidocbench-1.6-v1",
            "dataset_revision": "d386947f7fc3bafdcd756c8485845a2f43a19875",
            "dataset_pages": 1651,
            "gt_sha256": "a45cd84b04ad8b793e775089640e6b681209abea33ead54c1828ddca35fae496",
            "evaluator_revision": "147cd5ac9472002f5751221d390bf00abdbc0d2f",
            "evaluator_image": "ghcr.io/zeng-weijun/omnidocbench-eval@sha256:6116ad72172e763b5c43e963d5efebf2093f2362b975f58156ce4f6c9142e617",
            "config_sha256": "9ecdab12fa28c51cfcbac74cc9d701f8114b92fe628829453298a4c5693d5381",
        }
        if provenance != expected_provenance:
            errors.append("evaluator benchmark provenance mismatch")
        denominators = evaluator_payload.get("page_denominators") or {}
        if (denominators.get("display_formula") or {}).get("CDM", {}).get("ALL") != 313:
            errors.append("evaluator formula page denominator mismatch")
        if (denominators.get("table") or {}).get("TEDS", {}).get("ALL") != 458:
            errors.append("evaluator table page denominator mismatch")
        evaluator_metrics = extract_run_summary(evaluator_payload)
        if evaluator_metrics != result["accuracy"]["metrics"]:
            errors.append("evaluator summary does not reproduce accuracy metrics")
        if (result["accuracy"].get("source") or {}).get("sha256") != sha256_file(
            path.parent / "evaluator-summary.json"
        ):
            errors.append("accuracy source hash does not match evaluator summary")

        records = []
        for line_number, line in enumerate(
            (path.parent / "speed-records.jsonl").read_text(encoding="utf-8").splitlines(), 1
        ):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                errors.append(f"malformed speed record at line {line_number}")
                break
        if not errors:
            unique_names = sorted({record.get("image", "") for record in records})
            if "" in unique_names or sha256_lines(unique_names) != speed["sample_inventory_sha256"]:
                errors.append("speed record inventory hash mismatch")
            if {record.get("repetition") for record in records} != {1}:
                errors.append("speed records contain unexpected repetitions")
            recalculated = summarize_speed(
                records,
                float(speed["wall_seconds"]),
                speed["protocol_id"],
                speed["profile_id"],
                speed["sample_inventory_sha256"],
                speed["parameters"],
            )
            for key in (
                "status",
                "images",
                "requests",
                "successful",
                "failed",
                "truncated",
                "missing_completion_tokens",
                "request_seconds_sum",
                "average_latency_seconds",
                "page_per_second",
                "completion_tokens",
                "token_per_second",
                "latency_seconds",
            ):
                if recalculated.get(key) != speed.get(key):
                    errors.append(f"speed records do not reproduce summary field: {key}")
    if errors:
        raise ValueError(f"{path}: " + "; ".join(errors))
    return result


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
