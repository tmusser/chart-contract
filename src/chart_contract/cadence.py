"""Deterministic, opt-in cadence coverage for unaggregated trend dates."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, timedelta
from typing import Any

import pandas as pd

CADENCE_CONTRACT_KEY = "cadence_contract"
FREQUENCIES = ("daily", "weekly", "monthly")
_INPUTS = {"version", "date_field", "frequency", "require_complete"}
_RECEIPTS = {"start_date", "end_date", "observed_count", "expected_count", "missing_count", "missing_preview"}
_MAX_PERIODS = 10000
_PREVIEW_LIMIT = 5


def _date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"Cadence {field} must be a canonical ISO YYYY-MM-DD string.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Cadence {field} must be a canonical ISO YYYY-MM-DD string.") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"Cadence {field} must be a canonical ISO YYYY-MM-DD string.")
    return parsed


def chart_cadence_declaration(chart: Any) -> dict[str, Any] | None:
    freq = getattr(chart, "cadence_frequency", None)
    complete = getattr(chart, "cadence_require_complete", None)
    if freq is None and complete is None:
        return None
    return {
        "version": 1, "date_field": getattr(chart, "x", None),
        "frequency": freq, "require_complete": complete,
    }


def validate_cadence_declaration(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != _INPUTS:
        raise ValueError("Cadence declaration requires exactly the closed v1 input fields.")
    if type(value["version"]) is not int or value["version"] != 1:
        raise ValueError("Cadence contract version must equal 1.")
    if not isinstance(value["date_field"], str) or not value["date_field"].strip():
        raise ValueError("Cadence date_field must be a non-empty string.")
    if value["frequency"] not in FREQUENCIES or not isinstance(value["frequency"], str):
        raise ValueError("Cadence frequency must be daily, weekly, or monthly.")
    if type(value["require_complete"]) is not bool:
        raise ValueError("Cadence require_complete must be a boolean.")
    return dict(value)


def _next_date(day: date, frequency: str) -> date:
    if frequency == "daily":
        return day + timedelta(days=1)
    if frequency == "weekly":
        return day + timedelta(days=7)
    # Monthly cadence uses calendar-first anchor, not a fixed 30-day interval.
    if day.month == 12:
        return date(day.year + 1, 1, 1)
    return date(day.year, day.month + 1, 1)


def build_cadence_receipt(frame: pd.DataFrame, declaration: Mapping[str, Any]) -> dict[str, Any]:
    """Derive missing slots between observed min/max dates without filling rows."""
    parsed = validate_cadence_declaration(declaration)
    field = parsed["date_field"]
    if field not in frame.columns:
        raise ValueError(f"Cadence date_field {field!r} is absent from supplied evidence.")
    if frame.empty:
        raise ValueError("Cadence evidence must contain at least one observation.")
    observed = [_date(raw, f"row {index} date") for index, raw in enumerate(frame[field].tolist(), 1)]
    if len(observed) != len(set(observed)):
        raise ValueError("Cadence evidence contains duplicate period dates; aggregate or correct upstream.")
    unique = set(observed)
    first, last = min(unique), max(unique)
    if parsed["frequency"] == "monthly" and any(day.day != 1 for day in observed):
        raise ValueError("Monthly cadence requires first-of-month canonical dates.")
    expected = 0
    missing = 0
    preview: list[str] = []
    cursor = first
    while cursor <= last:
        expected += 1
        if expected > _MAX_PERIODS:
            raise ValueError(f"Cadence span exceeds the {_MAX_PERIODS} period safety limit.")
        if cursor not in unique:
            missing += 1
            if len(preview) < _PREVIEW_LIMIT:
                preview.append(cursor.isoformat())
        cursor = _next_date(cursor, parsed["frequency"])
    if expected != len(unique) + missing:
        raise ValueError("Cadence dates are off-grid for the declared frequency.")
    return {
        **parsed, "start_date": first.isoformat(), "end_date": last.isoformat(),
        "observed_count": len(observed), "expected_count": expected,
        "missing_count": missing, "missing_preview": preview,
    }


def parse_cadence_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or CADENCE_CONTRACT_KEY not in usermeta:
        return None
    raw = usermeta[CADENCE_CONTRACT_KEY]
    if not isinstance(raw, Mapping) or set(raw) != _INPUTS | _RECEIPTS:
        raise ValueError("usermeta.cadence_contract requires exactly the closed v1 fields.")
    declaration = validate_cadence_declaration({key: raw[key] for key in _INPUTS})
    start = _date(raw["start_date"], "start_date")
    end = _date(raw["end_date"], "end_date")
    if end < start:
        raise ValueError("Cadence end_date must be on or after start_date.")
    for key in ("observed_count", "expected_count", "missing_count"):
        if type(raw[key]) is not int or raw[key] < (0 if key == "missing_count" else 1):
            raise ValueError(f"Cadence {key} receipt must be a valid non-negative integer.")
    preview = raw["missing_preview"]
    if (not isinstance(preview, list) or len(preview) > _PREVIEW_LIMIT
            or any(not isinstance(day, str) for day in preview)):
        raise ValueError("Cadence missing_preview must be an array of at most five date strings.")
    for day in preview:
        _date(day, "missing_preview")
    if len(preview) > raw["missing_count"]:
        raise ValueError("Cadence preview cannot exceed missing_count.")
    return {**declaration, **{key: raw[key] for key in _RECEIPTS}}


def cadence_outcome(receipt: Mapping[str, Any]) -> tuple[str, str]:
    missing = receipt["missing_count"]
    total = receipt["expected_count"]
    if missing == 0:
        return "PASS", f"Cadence is complete: {total} expected {receipt['frequency']} period(s)."
    severity = "FAIL" if receipt["require_complete"] else "WARN"
    return severity, (
        f"Cadence gap: {missing} of {total} expected {receipt['frequency']} period(s) missing "
        f"between {receipt['start_date']} and {receipt['end_date']}; "
        f"first missing: {', '.join(receipt['missing_preview'])}."
    )
