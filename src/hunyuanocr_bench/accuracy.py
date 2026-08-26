from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import sha256_file
from .metrics import component_overall, normalize_accuracy


def _get(source: dict[str, Any], *keys: str) -> Any:
    value: Any = source
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise KeyError(".".join(keys))
        value = value[key]
    return value


def extract_metric_result(payload: dict[str, Any]) -> dict[str, float]:
    text_edit = float(_get(payload, "text_block", "all", "Edit_dist", "ALL_page_avg"))
    formula_cdm = float(_get(payload, "display_formula", "page", "CDM", "ALL"))
    table_teds = float(_get(payload, "table", "page", "TEDS", "ALL"))
    table_teds_s = float(_get(payload, "table", "page", "TEDS_structure_only", "ALL"))
    order_edit = float(_get(payload, "reading_order", "all", "Edit_dist", "ALL_page_avg"))
    overall = component_overall(text_edit, formula_cdm * 100.0, table_teds * 100.0)
    return normalize_accuracy(
        {
            "Overall": overall,
            "TextEdit": text_edit,
            "FormulaCDM": formula_cdm,
            "TableTEDS": table_teds,
            "TableTEDS_S": table_teds_s,
            "OrderEdit": order_edit,
        }
    ).as_dict()


def extract_run_summary(payload: dict[str, Any]) -> dict[str, float]:
    summary = _get(payload, "notebook_metric_summary")
    metrics = _get(summary, "metrics")
    source = {
        "Overall": _get(summary, "overall_notebook"),
        "TextEdit": _get(metrics, "text_block_Edit_dist", "notebook_value"),
        "FormulaCDM": _get(metrics, "display_formula_CDM", "notebook_value"),
        "TableTEDS": _get(metrics, "table_TEDS", "notebook_value"),
        "TableTEDS_S": _get(metrics, "table_TEDS_structure_only", "notebook_value"),
        "OrderEdit": _get(metrics, "reading_order_Edit_dist", "notebook_value"),
    }
    return normalize_accuracy(source).as_dict()


def build_accuracy_report(
    source_path: Path,
    protocol: dict[str, Any],
    machine: dict[str, Any],
) -> dict[str, Any]:
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    required = {"runtime_environment", "stage_execution", "page_denominators", "notebook_metric_summary"}
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"official v1.6 run summary is missing: {', '.join(missing)}")
    metrics = extract_run_summary(payload)
    reference = protocol["paper_reference"]["accuracy"]
    return {
        "status": "PASS",
        "protocol_id": protocol["protocol_id"],
        "dataset_pages": protocol["accuracy"]["expected_pages"],
        "metrics": metrics,
        "paper_reference": reference,
        "delta_from_paper": {
            "overall": round(metrics["overall"] - reference["overall"], 6),
            "text_edit": round(metrics["text_edit"] - reference["text_edit"], 6),
            "formula_cdm": round(metrics["formula_cdm"] - reference["formula_cdm"], 6),
            "table_teds": round(metrics["table_teds"] - reference["table_teds"], 6),
            "table_teds_s": round(metrics["table_teds_s"] - reference["table_teds_s"], 6),
            "order_edit": round(metrics["order_edit"] - reference["order_edit"], 6),
        },
        "machine_id": machine["machine_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {"path": str(source_path), "sha256": sha256_file(source_path)},
    }
