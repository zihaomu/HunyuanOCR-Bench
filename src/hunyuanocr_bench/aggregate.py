from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import load_json, load_machine, load_protocol, sha256_file
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
        "## Published Speed Results",
        "",
        "Rows are ordered by profile and then Page/s. Only rows with the same profile are directly comparable.",
        "",
        "| Machine | Accelerator | Profile | Avg latency (s)↓ | P95 (s)↓ | Page/s↑ | Token/s* |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for result in published_speed:
        accelerator = result["accelerator"]
        accelerator_label = f"{accelerator['count']}× {accelerator['model']}"
        speed = result["speed"]
        overview_lines.append(
            f"| [{result['machine_id']}]({result['machine_id']}/) | {accelerator_label} | "
            f"{speed['profile_id']} | {_f(speed['average_latency_seconds'], 3)} | "
            f"{_f(speed['latency_seconds']['p95'], 3)} | {_f(speed['page_per_second'], 4)} | "
            f"{_f(speed['token_per_second'], 1)} |"
        )
    if not published_speed:
        overview_lines.append("| - | - | - | - | - | - | - |")
    if references:
        overview_lines.extend(
            [
                "",
                "## Non-comparable Sampled References",
                "",
                "These samples are shown for visibility only. They do not use a publishable leaderboard profile and are not ranked against the table above.",
                "",
                "| Machine | Accelerator | Sample | Avg latency (s) | P95 (s) | Page/s | Token/s* |",
                "| --- | --- | --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for result in references:
            accelerator = result["accelerator"]
            accelerator_label = f"{accelerator['count']}× {accelerator['model']}"
            speed = result["speed"]
            overview_lines.append(
                f"| [{result['machine_id']}]({result['machine_id']}/) | {accelerator_label} | "
                f"{speed['profile_id']} | {_f(speed['average_latency_seconds'], 3)} | "
                f"{_f(speed['latency_seconds']['p95'], 3)} | {_f(speed['page_per_second'], 4)} | "
                f"{_f(speed['token_per_second'], 1)} |"
            )
    overview_lines.extend(["", "## Accuracy Status", ""])
    if results:
        overview_lines.append(
            f"{len(results)} complete accuracy result(s) are available in the [accuracy leaderboard](../leaderboards/accuracy.md)."
        )
    else:
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
