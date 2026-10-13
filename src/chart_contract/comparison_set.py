"""Explicit completeness semantics for truncated rank comparison sets."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from .contracts import is_ratio_like_unit
from .rank import RankSelection

COMPARISON_SET_CONTRACT_KEY = "comparison_set_contract"
COMPARISON_SET_CONTRACT_VERSION = 1
OMITTED_BEHAVIORS = {"exclude", "aggregate_other"}
OTHER_AGGREGATION = "sum"
OMITTED_MASS_WARN_SHARE = 0.50


@dataclass(frozen=True, slots=True)
class ComparisonSetSummary:
    category_field: str
    metric_field: str
    omitted_behavior: str
    other_label: str | None
    other_aggregation: str | None
    eligible_category_count: int
    selected_category_count: int
    omitted_category_count: int
    eligible_metric_total: float
    selected_metric_total: float
    omitted_metric_total: float
    selected_metric_share: float | None
    omitted_metric_share: float | None
    other_metric_value: float | None

    def to_dict(self) -> dict[str, Any]:
        return {"version": COMPARISON_SET_CONTRACT_VERSION, **asdict(self)}


def validate_omitted_behavior(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or value not in OMITTED_BEHAVIORS:
        raise ValueError("omitted_behavior must be 'exclude', 'aggregate_other', or None.")
    return value


def validate_other_label(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("other_label must be a non-empty string.")
    return value.strip()


def build_comparison_set_summary(
    frame: pd.DataFrame,
    *,
    selection: RankSelection,
    omitted_behavior: Any,
    other_label: Any = "Other",
    unit: str | None = None,
) -> ComparisonSetSummary:
    behavior = validate_omitted_behavior(omitted_behavior)
    if behavior is None:
        raise ValueError("Truncated rank comparison sets require explicit omitted_behavior.")
    if selection.summary.omitted_category_count <= 0:
        raise ValueError("comparison_set_contract requires at least one omitted eligible category.")

    category_field = selection.summary.category_field
    metric_field = selection.summary.metric_field
    if category_field not in frame.columns or metric_field not in frame.columns:
        raise ValueError("Comparison-set summary requires category and metric columns.")

    eligible = frame.loc[
        frame[category_field].notna() & frame[metric_field].notna(),
        [category_field, metric_field],
    ].copy()
    try:
        metrics = [float(value) for value in eligible[metric_field].tolist()]
    except (TypeError, ValueError) as exc:
        raise ValueError("Comparison-set metric values must be numeric.") from exc
    if any(not math.isfinite(value) for value in metrics):
        raise ValueError("Comparison-set metric values must be finite.")

    selected_ids = {_category_identity(value) for value in selection.displayed_categories}
    selected_mask = [
        _category_identity(value) in selected_ids
        for value in eligible[category_field].tolist()
    ]
    selected_metrics = [
        metric for metric, selected in zip(metrics, selected_mask) if selected
    ]
    omitted_metrics = [
        metric for metric, selected in zip(metrics, selected_mask) if not selected
    ]

    eligible_total = float(sum(metrics))
    selected_total = float(sum(selected_metrics))
    omitted_total = float(sum(omitted_metrics))
    share_available = all(value >= 0 for value in metrics) and eligible_total > 0
    selected_share = selected_total / eligible_total if share_available else None
    omitted_share = omitted_total / eligible_total if share_available else None

    normalized_label: str | None = None
    other_aggregation: str | None = None
    other_metric_value: float | None = None
    if behavior == "aggregate_other":
        if is_ratio_like_unit(unit):
            raise ValueError(
                "aggregate_other is not supported for percent/rate/ratio metrics because "
                "summing ratio-like values is not a valid generic completeness operation."
            )
        normalized_label = validate_other_label(other_label)
        category_ids = {_category_identity(value) for value in eligible[category_field].tolist()}
        if _category_identity(normalized_label) in category_ids:
            raise ValueError(
                f"other_label {normalized_label!r} collides with an eligible source category."
            )
        other_aggregation = OTHER_AGGREGATION
        other_metric_value = omitted_total

    return ComparisonSetSummary(
        category_field=category_field,
        metric_field=metric_field,
        omitted_behavior=behavior,
        other_label=normalized_label,
        other_aggregation=other_aggregation,
        eligible_category_count=selection.summary.eligible_category_count,
        selected_category_count=selection.summary.displayed_category_count,
        omitted_category_count=selection.summary.omitted_category_count,
        eligible_metric_total=eligible_total,
        selected_metric_total=selected_total,
        omitted_metric_total=omitted_total,
        selected_metric_share=selected_share,
        omitted_metric_share=omitted_share,
        other_metric_value=other_metric_value,
    )


def parse_comparison_set_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or COMPARISON_SET_CONTRACT_KEY not in usermeta:
        return None
    contract = usermeta.get(COMPARISON_SET_CONTRACT_KEY)
    if not isinstance(contract, Mapping):
        raise ValueError("usermeta.comparison_set_contract must be an object.")

    expected = {
        "version",
        "category_field",
        "metric_field",
        "omitted_behavior",
        "other_label",
        "other_aggregation",
        "eligible_category_count",
        "selected_category_count",
        "omitted_category_count",
        "eligible_metric_total",
        "selected_metric_total",
        "omitted_metric_total",
        "selected_metric_share",
        "omitted_metric_share",
        "other_metric_value",
    }
    if set(contract) != expected:
        missing = sorted(expected - set(contract))
        extra = sorted(set(contract) - expected)
        details: list[str] = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("unsupported: " + ", ".join(extra))
        raise ValueError(
            "usermeta.comparison_set_contract must use the exact v1 field set"
            + (" (" + "; ".join(details) + ")" if details else "")
            + "."
        )
    if contract.get("version") != COMPARISON_SET_CONTRACT_VERSION:
        raise ValueError(
            f"usermeta.comparison_set_contract.version must equal {COMPARISON_SET_CONTRACT_VERSION}."
        )

    category_field = _required_string(contract.get("category_field"), "category_field")
    metric_field = _required_string(contract.get("metric_field"), "metric_field")
    behavior = validate_omitted_behavior(contract.get("omitted_behavior"))
    if behavior is None:
        raise ValueError("usermeta.comparison_set_contract.omitted_behavior cannot be null.")

    counts: dict[str, int] = {}
    for name in ("eligible_category_count", "selected_category_count", "omitted_category_count"):
        value = contract.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(
                f"usermeta.comparison_set_contract.{name} must be a non-negative integer."
            )
        counts[name] = value
    if counts["selected_category_count"] + counts["omitted_category_count"] != counts["eligible_category_count"]:
        raise ValueError("comparison-set selected + omitted category counts must equal eligible count.")
    if counts["omitted_category_count"] <= 0:
        raise ValueError("comparison_set_contract requires at least one omitted category.")

    totals = {
        name: _finite_number(contract.get(name), name)
        for name in ("eligible_metric_total", "selected_metric_total", "omitted_metric_total")
    }
    if not math.isclose(
        totals["selected_metric_total"] + totals["omitted_metric_total"],
        totals["eligible_metric_total"],
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        raise ValueError("comparison-set selected + omitted metric totals must equal eligible total.")

    selected_share = _optional_share(contract.get("selected_metric_share"), "selected_metric_share")
    omitted_share = _optional_share(contract.get("omitted_metric_share"), "omitted_metric_share")
    if (selected_share is None) != (omitted_share is None):
        raise ValueError("comparison-set metric shares must both be null or both be numbers.")
    if selected_share is not None and not math.isclose(
        selected_share + omitted_share,
        1.0,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        raise ValueError("comparison-set selected + omitted metric shares must equal 1.")

    other_label = contract.get("other_label")
    other_aggregation = contract.get("other_aggregation")
    other_metric_value = contract.get("other_metric_value")
    if behavior == "exclude":
        if other_label is not None or other_aggregation is not None or other_metric_value is not None:
            raise ValueError("exclude comparison sets must not declare Other-bucket fields.")
    else:
        other_label = validate_other_label(other_label)
        if other_aggregation != OTHER_AGGREGATION:
            raise ValueError("aggregate_other comparison sets require other_aggregation='sum'.")
        other_metric_value = _finite_number(other_metric_value, "other_metric_value")
        if not math.isclose(
            other_metric_value,
            totals["omitted_metric_total"],
            rel_tol=1e-9,
            abs_tol=1e-9,
        ):
            raise ValueError("Other-bucket metric value must equal omitted_metric_total.")

    return {
        "version": COMPARISON_SET_CONTRACT_VERSION,
        "category_field": category_field,
        "metric_field": metric_field,
        "omitted_behavior": behavior,
        "other_label": other_label,
        "other_aggregation": other_aggregation,
        **counts,
        **totals,
        "selected_metric_share": selected_share,
        "omitted_metric_share": omitted_share,
        "other_metric_value": other_metric_value,
    }


def aggregate_other_transforms(
    *,
    category_field: str,
    metric_field: str,
    selected_categories: tuple[Any, ...] | list[Any],
    other_label: str,
) -> list[dict[str, Any]]:
    selected_json = json.dumps(list(selected_categories), ensure_ascii=False, separators=(",", ":"))
    field_json = json.dumps(category_field, ensure_ascii=False)
    label_json = json.dumps(other_label, ensure_ascii=False)
    expression = (
        f"indexof({selected_json}, datum[{field_json}]) >= 0 "
        f"? datum[{field_json}] : {label_json}"
    )
    return [
        {"calculate": expression, "as": category_field},
        {
            "aggregate": [
                {"op": OTHER_AGGREGATION, "field": metric_field, "as": metric_field}
            ],
            "groupby": [category_field],
        },
    ]


def comparison_set_sort(selection: RankSelection, summary: ComparisonSetSummary | None) -> list[Any]:
    values = list(selection.displayed_categories)
    if summary is not None and summary.omitted_behavior == "aggregate_other":
        values.append(summary.other_label)
    return values


def metric_mass_severity(summary: ComparisonSetSummary) -> str:
    if summary.omitted_behavior == "aggregate_other":
        return "PASS"
    if summary.omitted_metric_share is None:
        return "WARN"
    return "WARN" if summary.omitted_metric_share >= OMITTED_MASS_WARN_SHARE else "PASS"


def _category_identity(value: Any) -> tuple[str, str]:
    return type(value).__name__, str(value)


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"usermeta.comparison_set_contract.{field} must be a non-empty string.")
    return value.strip()


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"usermeta.comparison_set_contract.{field} must be a finite number.")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"usermeta.comparison_set_contract.{field} must be finite.")
    return numeric


def _optional_share(value: Any, field: str) -> float | None:
    if value is None:
        return None
    numeric = _finite_number(value, field)
    if numeric < 0 or numeric > 1:
        raise ValueError(f"usermeta.comparison_set_contract.{field} must be between 0 and 1.")
    return numeric
