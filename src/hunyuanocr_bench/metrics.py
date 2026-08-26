from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class AccuracyMetrics:
    overall: float
    text_edit: float
    formula_cdm: float
    table_teds: float
    table_teds_s: float
    order_edit: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


EVALUATOR_KEYS = {
    "overall": ("Overall", "overall"),
    "text_edit": ("Text Edit Distance", "TextEdit", "text_edit"),
    "formula_cdm": ("Formula CDM", "FormulaCDM", "formula_cdm"),
    "table_teds": ("Table TEDS", "TableTEDS", "table_teds"),
    "table_teds_s": (
        "Table TEDS Structure Only",
        "TableTEDS_S",
        "table_teds_s",
    ),
    "order_edit": ("Reading Order Edit Distance", "OrderEdit", "order_edit"),
}


def _number(source: Mapping[str, Any], names: tuple[str, ...]) -> float:
    for name in names:
        if name in source:
            value = source[name]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"metric {name!r} must be numeric")
            return float(value)
    raise KeyError(f"none of the metric keys are present: {', '.join(names)}")


def _score_percent(value: float, name: str) -> float:
    if 0.0 <= value <= 1.0:
        return value * 100.0
    if 0.0 <= value <= 100.0:
        return value
    raise ValueError(f"{name} must be in [0, 1] or [0, 100], found {value}")


def _edit_fraction(value: float, name: str) -> float:
    if 0.0 <= value <= 1.0:
        return value
    if 1.0 < value <= 100.0:
        return value / 100.0
    raise ValueError(f"{name} must be in [0, 1] or (1, 100], found {value}")


def component_overall(
    text_edit: float,
    formula_cdm: float,
    table_teds: float,
) -> float:
    """Return the official three-component OmniDocBench overall score."""
    return ((1.0 - text_edit) * 100.0 + formula_cdm + table_teds) / 3.0


def normalize_accuracy(source: Mapping[str, Any]) -> AccuracyMetrics:
    text_edit = _edit_fraction(_number(source, EVALUATOR_KEYS["text_edit"]), "TextEdit")
    formula_cdm = _score_percent(
        _number(source, EVALUATOR_KEYS["formula_cdm"]), "FormulaCDM"
    )
    table_teds = _score_percent(
        _number(source, EVALUATOR_KEYS["table_teds"]), "TableTEDS"
    )
    table_teds_s = _score_percent(
        _number(source, EVALUATOR_KEYS["table_teds_s"]), "TableTEDS_S"
    )
    order_edit = _edit_fraction(_number(source, EVALUATOR_KEYS["order_edit"]), "OrderEdit")
    overall = _score_percent(_number(source, EVALUATOR_KEYS["overall"]), "Overall")
    derived = component_overall(text_edit, formula_cdm, table_teds)

    # Published tables round components independently, so allow three hundredths.
    if abs(overall - derived) > 0.03:
        raise ValueError(
            f"Overall={overall:.6f} disagrees with component score={derived:.6f}"
        )

    return AccuracyMetrics(
        overall=overall,
        text_edit=text_edit,
        formula_cdm=formula_cdm,
        table_teds=table_teds,
        table_teds_s=table_teds_s,
        order_edit=order_edit,
    )
