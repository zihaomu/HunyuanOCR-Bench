from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import load_json, load_machine, load_protocol, sha256_file
from .metrics import normalize_accuracy
from .results import load_and_validate_result
from .speed import summarize_speed


def _f(value: Any, digits: int) -> str:
    return "-" if value is None else f"{float(value):.{digits}f}"


def _load_records(path: Path) -> list[dict[str, Any]]:
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        record = json.loads(line)
        if not isinstance(record, dict):
            raise ValueError(f"expected a JSON object at {path}:{line_number}")
        records.append(record)
    return records


def _machine_for_result(results_root: Path, machine_id: str) -> dict[str, Any]:
    path = results_root.parent / "machines" / f"{machine_id}.json"
    machine = load_machine(path)
    if machine["machine_id"] != machine_id:
        raise ValueError(f"machine profile does not match result path: {path}")
    return machine


def _load_speed_only(
    path: Path, results_root: Path, protocol: dict[str, Any]
) -> dict[str, Any]:
    speed = load_json(path)
    machine_id = path.parents[1].name
    machine = _machine_for_result(results_root, machine_id)
    profile_id = speed.get("profile_id")
    profile = protocol["speed_profiles"].get(profile_id)
    if not profile or profile.get("publishable") is not True:
        raise ValueError(f"speed-only result does not use a publishable profile: {path}")
    expected = {
        "status": "PASS",
        "protocol_id": protocol["protocol_id"],
        "sample_inventory_sha256": profile["sample_inventory_sha256"],
        "images": profile["expected_pages"],
        "requests": profile["expected_pages"] * profile["repetitions"],
    }
    for key, value in expected.items():
        if speed.get(key) != value:
            raise ValueError(f"speed-only result has invalid {key}: {path}")
    parameters = speed.get("parameters")
    if not isinstance(parameters, dict):
        raise ValueError(f"speed-only result is missing parameters: {path}")
    parameter_expected = {
        **profile["request"],
        "base_url": machine["runtime"]["base_url"],
        "model": machine["runtime"]["served_model_name"],
        "concurrency": 1,
        "warmup_pages": profile["warmup_pages"],
        "repetitions": profile["repetitions"],
        "image_data_url_mime": profile["image_data_url_mime"],
    }
    for key, value in parameter_expected.items():
        if parameters.get(key) != value:
            raise ValueError(f"speed-only result has invalid parameter {key}: {path}")
    records_path = path.parent / "speed-records.jsonl"
    rebuilt = summarize_speed(
        _load_records(records_path),
        wall_seconds=speed["wall_seconds"],
        protocol_id=speed["protocol_id"],
        profile_id=speed["profile_id"],
        sample_sha256=speed["sample_inventory_sha256"],
        parameters=parameters,
    )
    if rebuilt != speed:
        differences = sorted(
            key for key in rebuilt.keys() | speed.keys() if rebuilt.get(key) != speed.get(key)
        )
        raise ValueError(
            f"speed summary does not match request records ({', '.join(differences)}): {path}"
        )
    return {
        "kind": "speed-only",
        "publishable": True,
        "machine_id": machine_id,
        "run_id": path.parent.name,
        "accelerator": machine["accelerator"],
        "runtime": machine["runtime"],
        "speed": speed,
    }


def _load_sampled_speed(
    path: Path, results_root: Path, protocol: dict[str, Any]
) -> dict[str, Any]:
    sampled = load_json(path)
    machine_id = path.parents[1].name
    machine = _machine_for_result(results_root, machine_id)
    if sampled.get("machine_id") != machine_id:
        raise ValueError(f"sampled speed machine_id does not match result path: {path}")
    if sampled.get("protocol_id") != protocol["protocol_id"]:
        raise ValueError(f"sampled speed protocol_id mismatch: {path}")
    if sampled.get("status") != "SAMPLED" or sampled.get("publishable") is not False:
        raise ValueError(f"sampled speed result must be explicitly non-publishable: {path}")
    if sampled.get("accelerator") != machine["accelerator"] or sampled.get("runtime") != machine["runtime"]:
        raise ValueError(f"sampled speed hardware metadata does not match machine profile: {path}")
    sample = sampled.get("sample")
    metrics = sampled.get("metrics")
    request = sampled.get("request")
    if not isinstance(sample, dict) or not isinstance(metrics, dict) or not isinstance(request, dict):
        raise ValueError(f"sampled speed result is missing sample, metrics, or request: {path}")
    pages = sample.get("pages")
    source_pages = sample.get("source_measured_pages")
    if not isinstance(pages, int) or pages <= 0 or not isinstance(source_pages, int) or source_pages < pages:
        raise ValueError(f"sampled speed result has invalid page counts: {path}")
    if sample.get("selection_uses_performance_values") is not False or request.get("concurrency") != 1:
        raise ValueError(f"sampled speed selection or concurrency is invalid: {path}")
    artifacts = sampled.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError(f"sampled speed result is missing artifact hashes: {path}")
    artifact_names = {
        "speed_records_sha256": "speed-records.jsonl",
        "machine_profile_sha256": "machine.json",
        "machine_capture_sha256": "machine-capture.json",
        "assets_verification_sha256": "assets-verification.json",
    }
    for key, filename in artifact_names.items():
        artifact_path = path.parent / filename
        if artifacts.get(key) != sha256_file(artifact_path):
            raise ValueError(f"sampled speed artifact SHA-256 mismatch: {artifact_path}")
    if load_json(path.parent / "machine.json") != machine:
        raise ValueError(f"sampled speed machine artifact does not match machine profile: {path}")
    rebuilt = summarize_speed(
        _load_records(path.parent / "speed-records.jsonl"),
        wall_seconds=metrics["request_seconds_sum"],
        protocol_id=sampled["protocol_id"],
        profile_id="sampled",
        sample_sha256=sample["inventory_sha256"],
        parameters=request,
    )
    scalar_keys = (
        "requests", "successful", "failed", "truncated", "request_seconds_sum",
        "average_latency_seconds", "page_per_second", "completion_tokens", "token_per_second",
    )
    if any(metrics.get(key) != rebuilt.get(key) for key in scalar_keys):
        raise ValueError(f"sampled speed metrics do not match request records: {path}")
    latency_keys = ("p50", "p90", "p95", "p99", "min", "max")
    expected_latency = {key: rebuilt["latency_seconds"][key] for key in latency_keys}
    if metrics.get("latency_seconds") != expected_latency or rebuilt["images"] != pages:
        raise ValueError(f"sampled speed latency or page count does not match request records: {path}")
    return {
        "kind": "sampled-speed",
        "publishable": False,
        "machine_id": machine_id,
        "run_id": path.parent.name,
        "accelerator": machine["accelerator"],
        "runtime": machine["runtime"],
        "sample": sample,
        "speed": {
            "profile_id": f"sampled-{pages}-from-{source_pages}",
            "average_latency_seconds": metrics["average_latency_seconds"],
            "latency_seconds": metrics["latency_seconds"],
            "page_per_second": metrics["page_per_second"],
            "token_per_second": metrics["token_per_second"],
        },
    }


def _load_local_accuracy(
    path: Path, results_root: Path, protocol: dict[str, Any]
) -> dict[str, Any]:
    manifest = load_json(path)
    machine_id = path.parents[1].name
    machine = _machine_for_result(results_root, machine_id)
    expected_manifest = {
        "status": "PASS_LOCAL_EVALUATOR",
        "canonical": False,
        "protocol_id": protocol["protocol_id"],
        "dataset_pages": protocol["accuracy"]["expected_pages"],
        "evaluator_source_revision": protocol["evaluator"]["revision"],
        "config_sha256": protocol["evaluator"]["config_sha256"],
        "gt_sha256": protocol["dataset"]["gt_sha256"],
        "protocol_pinned_evaluator_image": protocol["evaluator"]["image"],
    }
    for key, value in expected_manifest.items():
        if manifest.get(key) != value:
            raise ValueError(f"local accuracy manifest has invalid {key}: {path}")
    directory_prefix = "local-evaluator-accuracy-"
    directory_name = path.parent.name
    if not directory_name.startswith(directory_prefix) or manifest.get("run_id") != f"{machine_id}-{directory_name.removeprefix(directory_prefix)}":
        raise ValueError(f"local accuracy run_id does not match result path: {path}")
    if (path.parent / "result.json").exists():
        raise ValueError(f"local accuracy directory must not contain result.json: {path.parent}")

    expected_artifacts = {
        "accuracy.json",
        "assets-verification.json",
        "evaluator-metric-result.json",
        "evaluator-run-summary.json",
        "evaluator-runtime-environment.json",
        "evaluator-stage-execution.json",
        "machine-capture-postrun.json",
        "machine-capture-run-start.json",
        "machine.json",
        "prediction-verification.json",
    }
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != expected_artifacts:
        raise ValueError(f"local accuracy manifest has an invalid artifact inventory: {path}")
    for filename, expected_sha256 in artifacts.items():
        artifact_path = path.parent / filename
        if expected_sha256 != sha256_file(artifact_path):
            raise ValueError(f"local accuracy artifact SHA-256 mismatch: {artifact_path}")
    if load_json(path.parent / "machine.json") != machine:
        raise ValueError(f"local accuracy machine artifact does not match machine profile: {path}")
    for filename in ("assets-verification.json", "prediction-verification.json"):
        gate_path = path.parent / filename
        if load_json(gate_path).get("status") != "PASS":
            raise ValueError(f"local accuracy gate is not PASS: {gate_path}")

    accuracy_path = path.parent / "accuracy.json"
    accuracy = load_json(accuracy_path)
    expected_accuracy = {
        "status": "PASS",
        "protocol_id": protocol["protocol_id"],
        "dataset_pages": protocol["accuracy"]["expected_pages"],
        "machine_id": machine_id,
        "paper_reference": protocol["paper_reference"]["accuracy"],
    }
    for key, value in expected_accuracy.items():
        if accuracy.get(key) != value:
            raise ValueError(f"local accuracy result has invalid {key}: {accuracy_path}")
    metrics = accuracy.get("metrics")
    if not isinstance(metrics, dict) or normalize_accuracy(metrics).as_dict() != metrics:
        raise ValueError(f"local accuracy metrics are invalid or not normalized: {accuracy_path}")
    source = accuracy.get("source")
    if not isinstance(source, dict) or source.get("sha256") != artifacts["evaluator-run-summary.json"]:
        raise ValueError(f"local accuracy source does not match evaluator summary: {accuracy_path}")

    actual_evaluator = manifest.get("actual_evaluator_base")
    if not isinstance(actual_evaluator, dict) or not actual_evaluator.get("repo_digest"):
        raise ValueError(f"local accuracy manifest is missing evaluator runtime: {path}")
    if actual_evaluator["repo_digest"] == protocol["evaluator"]["image"]:
        raise ValueError(f"local accuracy evidence unexpectedly used the canonical image: {path}")
    return {
        "kind": "local-evaluator",
        "canonical": False,
        "machine_id": machine_id,
        "run_id": manifest["run_id"],
        "relative_dir": path.parent.relative_to(results_root).as_posix(),
        "accelerator": machine["accelerator"],
        "runtime": machine["runtime"],
        "accuracy": accuracy,
        "actual_evaluator_base": actual_evaluator,
    }


def aggregate_results(
    results_root: Path, output_dir: Path, protocol: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    protocol = protocol or load_protocol()
    paths = sorted(results_root.glob("*/*/result.json")) if results_root.exists() else []
    results = []
    for path in paths:
        result = load_and_validate_result(path)
        if path.parents[1].name != result["machine_id"]:
            raise ValueError(f"result path does not match machine_id: {path}")
        if path.parent.name != result["run_id"]:
            raise ValueError(f"result path does not match run_id: {path}")
        results.append(result)
    run_ids = [result["run_id"] for result in results]
    if len(run_ids) != len(set(run_ids)):
        raise ValueError("duplicate run_id values in results tree")
    results.sort(key=lambda item: (-item["accuracy"]["metrics"]["overall"], item["machine_id"]))
    results_root.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "all-results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    speed_results = []
    for result in results:
        profile = protocol["speed_profiles"].get(result["speed"]["profile_id"], {})
        speed_results.append(
            {
                "kind": "complete",
                "publishable": profile.get("publishable") is True,
                "machine_id": result["machine_id"],
                "run_id": result["run_id"],
                "accelerator": result["accelerator"],
                "runtime": result["runtime"],
                "speed": result["speed"],
            }
        )
    speed_paths = sorted(results_root.glob("*/*/speed.json")) if results_root.exists() else []
    speed_results.extend(
        _load_speed_only(path, results_root, protocol)
        for path in speed_paths
        if not (path.parent / "result.json").exists()
    )
    sampled_paths = sorted(results_root.glob("*/*/sampled-speed.json")) if results_root.exists() else []
    speed_results.extend(_load_sampled_speed(path, results_root, protocol) for path in sampled_paths)
    speed_results.sort(
        key=lambda item: (
            not item["publishable"], item["speed"]["profile_id"],
            -item["speed"]["page_per_second"], item["machine_id"],
        )
    )
    (output_dir / "speed-results.json").write_text(
        json.dumps(speed_results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    published_speed = [item for item in speed_results if item["publishable"]]
    references = [item for item in speed_results if not item["publishable"]]

    local_accuracy_paths = (
        sorted(results_root.glob("*/local-evaluator-accuracy-*/manifest.json"))
        if results_root.exists() else []
    )
    local_accuracy = [_load_local_accuracy(path, results_root, protocol) for path in local_accuracy_paths]

    accuracy_lines = [
        "# Accuracy Leaderboard",
        "",
        "OmniDocBench v1.6, 1651 pages. Overall is the official mean of Text score, Formula CDM, and Table TEDS.",
        "",
        "| Machine | Accelerator | Model Type | Model Size | Overall↑ | TextEdit↓ | FormulaCDM↑ | TableTEDS↑ | TableTEDS_S↑ | OrderEdit↓ |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    speed_lines = [
        "# Speed Leaderboard",
        "",
        "Only rows with the same speed profile are directly comparable. Page/s is the primary cross-hardware metric.",
        "",
        "## Published Speed Results",
        "",
        "| Machine | Accelerator | Framework | Method | Profile | Avg latency (s)↓ | P95 (s)↓ | Page/s↑ | Token/s* |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for result in results:
        accelerator = result["accelerator"]
        accelerator_label = f"{accelerator['count']}× {accelerator['model']}"
        model = result["model"]
        metrics = result["accuracy"]["metrics"]
        accuracy_lines.append(
            f"| {result['machine_id']} | {accelerator_label} | {model['type']} | {model['size']} | "
            f"{_f(metrics['overall'], 2)} | {_f(metrics['text_edit'], 3)} | "
            f"{_f(metrics['formula_cdm'], 2)} | {_f(metrics['table_teds'], 2)} | "
            f"{_f(metrics['table_teds_s'], 2)} | {_f(metrics['order_edit'], 3)} |"
        )
    for result in published_speed:
        accelerator = result["accelerator"]
        accelerator_label = f"{accelerator['count']}× {accelerator['model']}"
        speed = result["speed"]
        runtime = result["runtime"]
        speed_lines.append(
            f"| {result['machine_id']} | {accelerator_label} | {runtime['framework']} | "
            f"{runtime['inference_method']} | {speed['profile_id']} | "
            f"{_f(speed['average_latency_seconds'], 3)} | {_f(speed['latency_seconds']['p95'], 3)} | "
            f"{_f(speed['page_per_second'], 4)} | {_f(speed['token_per_second'], 1)} |"
        )
    if references:
        speed_lines.extend(
            [
                "",
                "## Non-comparable References",
                "",
                "These diagnostic or sampled results are shown for visibility only. They must not be ranked against published rows.",
                "",
                "| Machine | Accelerator | Framework | Method | Profile/sample | Avg latency (s) | P95 (s) | Page/s | Token/s* |",
                "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for result in references:
            accelerator = result["accelerator"]
            accelerator_label = f"{accelerator['count']}× {accelerator['model']}"
            speed = result["speed"]
            runtime = result["runtime"]
            speed_lines.append(
                f"| {result['machine_id']} | {accelerator_label} | {runtime['framework']} | "
                f"{runtime['inference_method']} | {speed['profile_id']} | "
                f"{_f(speed['average_latency_seconds'], 3)} | {_f(speed['latency_seconds']['p95'], 3)} | "
                f"{_f(speed['page_per_second'], 4)} | {_f(speed['token_per_second'], 1)} |"
            )
    speed_lines.extend(["", "\\* Token/s is diagnostic only and is not comparable across different tokenizers."])

    overview_lines = [
        "# Results Overview",
        "",
        "This page summarizes the machine results currently merged into `main`. Values are generated from validated evidence in each machine directory.",
        "",
        "## Speed Results",
        "",
        "Rows are ordered by Page/s. The Profile column identifies the measurement inventory used for each result.",
        "",
        "| Machine | Accelerator | Profile | Avg latency (s)↓ | P95 (s)↓ | Page/s↑ | Token/s* |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    overview_speed = sorted(
        speed_results,
        key=lambda item: (-item["speed"]["page_per_second"], item["machine_id"]),
    )
    for result in overview_speed:
        accelerator = result["accelerator"]
        accelerator_label = f"{accelerator['count']}× {accelerator['model']}"
        speed = result["speed"]
        overview_lines.append(
            f"| [{result['machine_id']}]({result['machine_id']}/) | {accelerator_label} | "
            f"{speed['profile_id']} | {_f(speed['average_latency_seconds'], 3)} | "
            f"{_f(speed['latency_seconds']['p95'], 3)} | {_f(speed['page_per_second'], 4)} | "
            f"{_f(speed['token_per_second'], 1)} |"
        )
    if not overview_speed:
        overview_lines.append("| - | - | - | - | - | - | - |")
    overview_lines.extend(["", "## Accuracy Status", ""])
    if results:
        overview_lines.append(
            f"{len(results)} canonical accuracy result(s) are available in the [accuracy leaderboard](../leaderboards/accuracy.md):"
        )
        overview_lines.append("")
        for result in results:
            metrics = result["accuracy"]["metrics"]
            overview_lines.append(
                f"- [{result['machine_id']}]({result['machine_id']}/{result['run_id']}/result.json): "
                f"Overall {_f(metrics['overall'], 6)}"
            )
    if local_accuracy:
        overview_lines.extend(["", f"{len(local_accuracy)} complete local-evaluator result(s):", ""])
        for result in local_accuracy:
            metrics = result["accuracy"]["metrics"]
            overview_lines.append(
                f"- [{result['machine_id']}]({result['relative_dir']}/README.md): "
                f"Overall {_f(metrics['overall'], 6)} (non-canonical evaluator runtime)"
            )
    if not results and not local_accuracy:
        overview_lines.append(
            "No complete accuracy result has been published yet. Accuracy requires full 1,651-page inference and the official OmniDocBench evaluator."
        )
    overview_lines.extend(
        [
            "",
            "## Detailed Outputs",
            "",
            "- [Speed leaderboard](../leaderboards/speed.md)",
            "- [Structured speed results](../leaderboards/speed-results.json)",
            "- [Accuracy leaderboard](../leaderboards/accuracy.md)",
            "",
            "\\* Token/s is diagnostic only and is not comparable across different tokenizers.",
        ]
    )
    (output_dir / "accuracy.md").write_text("\n".join(accuracy_lines) + "\n", encoding="utf-8")
    (output_dir / "speed.md").write_text("\n".join(speed_lines) + "\n", encoding="utf-8")
    (results_root / "README.md").write_text("\n".join(overview_lines) + "\n", encoding="utf-8")
    return results
