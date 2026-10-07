"""Deterministic baseline-comparison contracts."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from .contracts import is_percent_unit, is_supported_percent_representation

COMPARISON_CONTRACT_KEY = "comparison_contract"
COMPARISON_CONTRACT_VERSION = 1
COMPARISON_INTENTS = {"trend", "compare"}
CHANGE_TYPES = {"absolute", "percentage_points", "percent_change", "ratio"}


@dataclass(frozen=True, slots=True)
class ComparisonSummary:
    metric_field: str
    baseline_field: str
    baseline_value: str | int | float
    target_value: str | int | float
    change_type: str
    declared_change: float
    baseline_metric_value: float
    target_metric_value: float
    computed_change: float

    def to_dict(self) -> dict[str, Any]:
        return {"version": COMPARISON_CONTRACT_VERSION, **asdict(self)}


def comparison_declaration(chart: Any) -> dict[str, Any] | None:
    values = (
        getattr(chart, "baseline_field", None),
        getattr(chart, "baseline_value", None),
        getattr(chart, "target_value", None),
        getattr(chart, "change_type", None),
        getattr(chart, "declared_change", None),
    )
    if all(value is None for value in values):
        return None
    return {
        "metric_field": getattr(chart, "y", None),
        "baseline_field": getattr(chart, "baseline_field", None),
        "baseline_value": getattr(chart, "baseline_value", None),
        "target_value": getattr(chart, "target_value", None),
        "change_type": getattr(chart, "change_type", None),
        "declared_change": getattr(chart, "declared_change", None),
    }


def build_comparison_summary(
    frame: pd.DataFrame,
    *,
    metric_field: Any,
    baseline_field: Any,
    baseline_value: Any,
    target_value: Any,
    change_type: Any,
    declared_change: Any,
    unit: str | None,
    value_representation: str | None,
) -> ComparisonSummary:
    metric = _required_string(metric_field, "metric_field")
    selector = _required_string(baseline_field, "baseline_field")
    baseline_selector = _selector_value(baseline_value, "baseline_value")
    target_selector = _selector_value(target_value, "target_value")
    if baseline_selector == target_selector:
        raise ValueError("Baseline and target selector values must be different.")

    kind = _change_type(change_type)
    declared = _finite_number(declared_change, "declared_change")

    baseline_metric, target_metric = select_metric_pair(
        frame,
        metric_field=metric,
        baseline_field=selector,
        baseline_value=baseline_selector,
        target_value=target_selector,
    )
    computed = compute_change(
        baseline_metric,
        target_metric,
        change_type=kind,
        unit=unit,
        value_representation=value_representation,
    )

    return ComparisonSummary(
        metric_field=metric,
        baseline_field=selector,
        baseline_value=baseline_selector,
        target_value=target_selector,
        change_type=kind,
        declared_change=declared,
        baseline_metric_value=baseline_metric,
        target_metric_value=target_metric,
        computed_change=computed,
    )


def parse_comparison_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or COMPARISON_CONTRACT_KEY not in usermeta:
        return None

    contract = usermeta.get(COMPARISON_CONTRACT_KEY)
    if not isinstance(contract, Mapping):
        raise ValueError("usermeta.comparison_contract must be an object.")

    expected_fields = {
        "version",
        "metric_field",
        "baseline_field",
        "baseline_value",
        "target_value",
        "change_type",
        "declared_change",
        "baseline_metric_value",
        "target_metric_value",
        "computed_change",
    }
    if set(contract) != expected_fields:
        missing = sorted(expected_fields - set(contract))
        extra = sorted(set(contract) - expected_fields)
        details: list[str] = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("unsupported: " + ", ".join(extra))
        raise ValueError(
            "usermeta.comparison_contract must use the exact v1 field set"
            + (" (" + "; ".join(details) + ")" if details else "")
            + "."
        )

    if contract.get("version") != COMPARISON_CONTRACT_VERSION:
        raise ValueError(
            f"usermeta.comparison_contract.version must equal {COMPARISON_CONTRACT_VERSION}."
        )

    return {
        "version": COMPARISON_CONTRACT_VERSION,
        "metric_field": _required_string(contract.get("metric_field"), "metric_field"),
        "baseline_field": _required_string(contract.get("baseline_field"), "baseline_field"),
        "baseline_value": _selector_value(contract.get("baseline_value"), "baseline_value"),
        "target_value": _selector_value(contract.get("target_value"), "target_value"),
        "change_type": _change_type(contract.get("change_type")),
        "declared_change": _finite_number(contract.get("declared_change"), "declared_change"),
        "baseline_metric_value": _finite_number(
            contract.get("baseline_metric_value"),
            "baseline_metric_value",
        ),
        "target_metric_value": _finite_number(
            contract.get("target_metric_value"),
            "target_metric_value",
        ),
        "computed_change": _finite_number(contract.get("computed_change"), "computed_change"),
    }


def select_metric_pair(
    frame: pd.DataFrame,
    *,
    metric_field: str,
    baseline_field: str,
    baseline_value: str | int | float,
    target_value: str | int | float,
) -> tuple[float, float]:
    if baseline_field not in frame.columns:
        raise ValueError(f"Baseline selector field {baseline_field!r} is missing from the data.")
    if metric_field not in frame.columns:
        raise ValueError(f"Comparison metric field {metric_field!r} is missing from the data.")

    baseline_rows = frame.loc[frame[baseline_field] == baseline_value]
    target_rows = frame.loc[frame[baseline_field] == target_value]
    if len(baseline_rows) != 1:
        raise ValueError(
            f"Baseline selector {baseline_field}={baseline_value!r} matched "
            f"{len(baseline_rows)} rows; exactly one is required."
        )
    if len(target_rows) != 1:
        raise ValueError(
            f"Target selector {baseline_field}={target_value!r} matched "
            f"{len(target_rows)} rows; exactly one is required."
        )

    baseline_raw = baseline_rows.iloc[0][metric_field]
    target_raw = target_rows.iloc[0][metric_field]
    if pd.isna(baseline_raw) or pd.isna(target_raw):
        raise ValueError("Baseline and target metric values must both be non-null.")
    if isinstance(baseline_raw, bool) or isinstance(target_raw, bool):
        raise ValueError("Baseline and target metric values must be numeric, not boolean.")
    try:
        baseline_metric = float(baseline_raw)
        target_metric = float(target_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("Baseline and target metric values must be numeric.") from exc
    if not math.isfinite(baseline_metric) or not math.isfinite(target_metric):
        raise ValueError("Baseline and target metric values must be finite.")
    return baseline_metric, target_metric


def compute_change(
    baseline: float,
    target: float,
    *,
    change_type: str,
    unit: str | None,
    value_representation: str | None,
) -> float:
    if change_type == "absolute":
        return target - baseline
    if change_type == "percentage_points":
        if not is_percent_unit(unit):
            raise ValueError("percentage_points change requires an explicit percent unit.")
        if not is_supported_percent_representation(value_representation):
            raise ValueError(
                "percentage_points change requires value_representation='fraction' "
                "or 'percentage_points'."
            )
        delta = target - baseline
        return delta * 100.0 if value_representation == "fraction" else delta
    if change_type == "percent_change":
        if baseline == 0:
            raise ValueError("percent_change is undefined when the baseline metric is zero.")
        return ((target - baseline) / baseline) * 100.0
    if change_type == "ratio":
        if baseline == 0:
            raise ValueError("ratio change is undefined when the baseline metric is zero.")
        return target / baseline
    raise ValueError(f"Unsupported comparison change_type: {change_type!r}.")


def changes_match(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-9)


def explicit_claim_change(
    claim: str | None,
    *,
    unit: str | None,
) -> tuple[str, float] | None:
    """Recover only narrow, explicit numeric change language from a claim."""

    text = (claim or "").strip()
    if not text:
        return None

    point_pattern = (
        r"(?P<value>[+-]?\d+(?:\.\d+)?)\s*"
        r"(?P<label>percentage\s+points?|percent(?:age)?[-\s]?points?|pp)\b"
    )
    match = re.search(point_pattern, text, flags=re.IGNORECASE)
    if match:
        return "percentage_points", float(match.group("value"))

    if is_percent_unit(unit):
        match = re.search(
            r"(?P<value>[+-]?\d+(?:\.\d+)?)\s+points?\b",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            return "percentage_points", float(match.group("value"))

    match = re.search(
        r"(?P<value>[+-]?\d+(?:\.\d+)?)\s*(?:%|percent\b)",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return "percent_change", float(match.group("value"))

    match = re.search(
        r"(?P<value>[+-]?\d+(?:\.\d+)?)\s*(?:[x×]|times\b)",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return "ratio", float(match.group("value"))

    return None


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"comparison contract {field} must be a non-empty string.")
    return value.strip()


def _selector_value(value: Any, field: str) -> str | int | float:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError(f"comparison contract {field} must be a string or finite number.")
    if isinstance(value, str):
        if not value.strip():
            raise ValueError(f"comparison contract {field} must not be blank.")
        return value.strip()
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"comparison contract {field} must be finite.")
    return value


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"comparison contract {field} must be a finite number.")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"comparison contract {field} must be finite.")
    return numeric


def _change_type(value: Any) -> str:
    if not isinstance(value, str) or value not in CHANGE_TYPES:
        raise ValueError(
            "comparison contract change_type must be one of "
            "'absolute', 'percentage_points', 'percent_change', or 'ratio'."
        )
    return value
