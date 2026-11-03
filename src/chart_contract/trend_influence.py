"""Opt-in leave-one-out linear trend sensitivity, not statistical inference."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
import math
from numbers import Real
from typing import Any

import pandas as pd

CONTRACT_KEY = "trend_influence_contract"
INPUT_FIELDS = ("version", "x_field", "y_field")
RECEIPT_FIELDS = (
    "x_kind", "row_count", "full_slope", "loo_min_slope",
    "loo_max_slope", "flat_tolerance", "reversal_count", "reversal_preview",
)
MIN_POINTS = 5
MAX_POINTS = 2000
PREVIEW_LIMIT = 5
FLAT_RELATIVE_TOLERANCE = 1e-10


def chart_influence_declaration(chart: Any) -> dict[str, Any] | None:
    enabled = getattr(chart, "trend_influence", None)
    if enabled is None or enabled is False:
        return None
    if enabled is not True:
        raise ValueError("trend_influence must be a boolean (True to opt in).")
    return {
        "version": 1,
        "x_field": getattr(chart, "x", None),
        "y_field": getattr(chart, "y", None),
    }


def validate_declaration(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) != set(INPUT_FIELDS):
        raise ValueError("Trend influence declaration requires exactly the closed v1 fields.")
    if type(raw["version"]) is not int or raw["version"] != 1:
        raise ValueError("Trend influence version must equal 1.")
    if any(not isinstance(raw[name], str) or not raw[name].strip()
           for name in ("x_field", "y_field")):
        raise ValueError("Trend influence x_field and y_field must be non-empty strings.")
    if raw["x_field"] == raw["y_field"]:
        raise ValueError("Trend influence x_field and y_field must be distinct.")
    return {key: raw[key] for key in INPUT_FIELDS}


def _numeric(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"Trend influence {label} must be finite numeric.")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"Trend influence {label} must be finite numeric.")
    return result


def _canonical_date(raw: str, label: str) -> date:
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"Trend influence {label} must use canonical YYYY-MM-DD dates.") from exc
    if parsed.isoformat() != raw:
        raise ValueError(f"Trend influence {label} must use canonical YYYY-MM-DD dates.")
    return parsed


def _parse_x(raw_values: list[Any]) -> tuple[list[float], list[str], str]:
    if all(isinstance(v, str) for v in raw_values):
        dates = [_canonical_date(v, f"row {i} x") for i, v in enumerate(raw_values, 1)]
        origin = min(dates)
        return (
            [float((day - origin).days) for day in dates],
            [day.isoformat() for day in dates],
            "date",
        )
    if not all(isinstance(v, Real) and not isinstance(v, bool) for v in raw_values):
        raise ValueError("Trend influence x must be uniformly finite numeric or canonical ISO date strings.")
    values = [_numeric(v, f"row {i} x") for i, v in enumerate(raw_values, 1)]
    origin = min(values)
    centered = [value - origin for value in values]
    if not all(math.isfinite(value) for value in centered):
        raise ValueError("Trend influence x spread is not finite.")
    return centered, [format(value, ".17g") for value in values], "numeric"


def _slope(x: list[float], y: list[float]) -> float:
    n = len(x)
    xm = math.fsum(x) / n
    ym = math.fsum(y) / n
    ssx = math.fsum((xi - xm) ** 2 for xi in x)
    if not math.isfinite(ssx) or ssx <= 0:
        raise ValueError("Trend influence slope requires x values with nonzero finite variance.")
    sxy = math.fsum((xi - xm) * (yi - ym) for xi, yi in zip(x, y))
    result = sxy / ssx
    if not math.isfinite(result):
        raise ValueError("Trend influence slope computation was not finite.")
    return result


def _direction(slope: float, tolerance: float) -> int:
    if slope > tolerance:
        return 1
    if slope < -tolerance:
        return -1
    return 0


def build_influence_receipt(frame: pd.DataFrame, declaration: Mapping[str, Any]) -> dict[str, Any]:
    parsed = validate_declaration(declaration)
    x_field, y_field = parsed["x_field"], parsed["y_field"]
    if x_field not in frame.columns or y_field not in frame.columns:
        raise ValueError("Trend influence x_field and y_field must exist in the supplied source evidence.")
    n = len(frame)
    if not MIN_POINTS <= n <= MAX_POINTS:
        raise ValueError(
            f"Trend influence needs {MIN_POINTS}–{MAX_POINTS} complete observations; received {n}."
        )
    x, labels, x_kind = _parse_x(frame[x_field].tolist())
    y = [_numeric(raw, f"row {i} y") for i, raw in enumerate(frame[y_field].tolist(), 1)]
    if len(set(x)) != n:
        raise ValueError("Trend influence requires unique x observations; aggregate duplicates upstream.")
    x_span = max(x) - min(x)
    y_span = max(y) - min(y)
    if not math.isfinite(x_span) or x_span <= 0 or not math.isfinite(y_span):
        raise ValueError("Trend influence input spreads must be finite.")
    tolerance = FLAT_RELATIVE_TOLERANCE * (y_span / x_span)
    if not math.isfinite(tolerance):
        raise ValueError("Trend influence direction tolerance is not finite.")
    full = _slope(x, y)
    loo: list[float] = []
    reversals: list[tuple[float, str]] = []
    full_direction = _direction(full, tolerance)
    for i in range(n):
        leave_one_out = _slope(x[:i] + x[i+1:], y[:i] + y[i+1:])
        loo.append(leave_one_out)
        if full_direction and _direction(leave_one_out, tolerance) == -full_direction:
            reversals.append((x[i], labels[i]))
    reversals.sort()
    return {
        **parsed,
        "x_kind": x_kind,
        "row_count": n,
        "full_slope": full,
        "loo_min_slope": min(loo),
        "loo_max_slope": max(loo),
        "flat_tolerance": tolerance,
        "reversal_count": len(reversals),
        "reversal_preview": [label for _, label in reversals[:PREVIEW_LIMIT]],
    }


def parse_influence_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    meta = spec.get("usermeta")
    if not isinstance(meta, Mapping) or CONTRACT_KEY not in meta:
        return None
    raw = meta[CONTRACT_KEY]
    if not isinstance(raw, Mapping) or set(raw) != set(INPUT_FIELDS) | set(RECEIPT_FIELDS):
        raise ValueError("usermeta.trend_influence_contract requires exactly the closed v1 fields.")
    parsed = validate_declaration({key: raw[key] for key in INPUT_FIELDS})
    if raw["x_kind"] not in ("numeric", "date"):
        raise ValueError("Trend influence x_kind must be numeric or date.")
    if type(raw["row_count"]) is not int or not MIN_POINTS <= raw["row_count"] <= MAX_POINTS:
        raise ValueError("Trend influence row_count receipt is invalid.")
    for field in ("full_slope", "loo_min_slope", "loo_max_slope", "flat_tolerance"):
        _numeric(raw[field], field)
    if raw["flat_tolerance"] < 0 or raw["loo_min_slope"] > raw["loo_max_slope"]:
        raise ValueError("Trend influence numeric receipts are inconsistent.")
    if type(raw["reversal_count"]) is not int or not 0 <= raw["reversal_count"] <= raw["row_count"]:
        raise ValueError("Trend influence reversal_count receipt is invalid.")
    preview = raw["reversal_preview"]
    if (not isinstance(preview, list) or len(preview) > PREVIEW_LIMIT
            or len(preview) > raw["reversal_count"]
            or any(not isinstance(item, str) or not item for item in preview)):
        raise ValueError("Trend influence reversal_preview receipt is invalid.")
    return {**parsed, **{key: raw[key] for key in RECEIPT_FIELDS}}


def influence_outcome(receipt: Mapping[str, Any]) -> tuple[str, str]:
    count = receipt["reversal_count"]
    if count:
        return (
            "WARN",
            f"Influential observation sensitivity: omitting {count} individual point(s) "
            f"separately reverses the full-data OLS trend direction. "
            f"First reversing x value(s): {', '.join(receipt['reversal_preview'])}. "
            "This is descriptive sensitivity, not statistical significance or causation.",
        )
    return (
        "PASS",
        f"No leave-one-out OLS slope sign reversal among {receipt['row_count']} "
        "points under the declared numerical flatness tolerance.",
    )
