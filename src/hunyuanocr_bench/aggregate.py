from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .results import load_and_validate_result


def _f(value: Any, digits: int) -> str:
    return "-" if value is None else f"{float(value):.{digits}f}"


def aggregate_results(results_root: Path, output_dir: Path) -> list[dict[str, Any]]:
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
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "all-results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

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
    speed_results = sorted(
        results, key=lambda item: (-item["speed"]["page_per_second"], item["machine_id"])
    )
    for result in speed_results:
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
    (output_dir / "accuracy.md").write_text("\n".join(accuracy_lines) + "\n", encoding="utf-8")
    (output_dir / "speed.md").write_text("\n".join(speed_lines) + "\n", encoding="utf-8")
    return results
