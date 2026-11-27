"""Deterministic, opt-in cadence coverage for unaggregated trend dates."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, timedelta
from typing import Any

import pandas as pd

CADENCE_CONTRACT_KEY = "cadence_contract"
FREQUENCIES = ("daily", "weekly", "monthly")
_INPUTS = {"version", "date_field", "frequency", "require_complete"}
_INPUTS_V2 = _INPUTS | {"expected_start", "expected_end"}
_RECEIPTS = {"start_date", "end_date", "observed_count", "expected_count", "missing_count", "missing_preview"}
_BOUNDARY_RECEIPTS = {
    "expected_window_count", "leading_missing_count",
    "trailing_missing_count", "boundary_missing_preview",
}
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
    # Grouped grids have separate receipts; preserve legacy single-series v1/v2.
    if getattr(chart, "cadence_expected_groups", None) is not None:
        return None
    freq = getattr(chart, "cadence_frequency", None)
    complete = getattr(chart, "cadence_require_complete", None)
    start = getattr(chart, "cadence_expected_start", None)
    end = getattr(chart, "cadence_expected_end", None)
    if all(value is None for value in (freq, complete, start, end)):
        return None
    declared = {
        "version": 2 if start is not None or end is not None else 1,
        "date_field": getattr(chart, "x", None),
        "frequency": freq, "require_complete": complete,
    }
    if declared["version"] == 2:
        declared.update(expected_start=start, expected_end=end)
    return declared


def validate_cadence_declaration(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("Cadence declaration must be an object.")
    version = value.get("version")
    if type(version) is not int or version not in (1, 2):
        raise ValueError("Cadence contract version must equal 1 or 2.")
    expected_keys = _INPUTS if version == 1 else _INPUTS_V2
    if set(value) != expected_keys:
        raise ValueError(f"Cadence declaration requires exactly the closed v{version} input fields.")
    if not isinstance(value["date_field"], str) or not value["date_field"].strip():
        raise ValueError("Cadence date_field must be a non-empty string.")
    if not isinstance(value["frequency"], str) or value["frequency"] not in FREQUENCIES:
        raise ValueError("Cadence frequency must be daily, weekly, or monthly.")
    if type(value["require_complete"]) is not bool:
        raise ValueError("Cadence require_complete must be a boolean.")
    if version == 2:
        start = value["expected_start"]
        end = value["expected_end"]
        if start is None and end is None:
            raise ValueError("Cadence v2 requires at least one declared expected window boundary.")
        for key, raw in (("expected_start", start), ("expected_end", end)):
            if raw is not None:
                parsed = _date(raw, key)
                if value["frequency"] == "monthly" and parsed.day != 1:
                    raise ValueError("Monthly cadence boundaries must be first-of-month dates.")
        if start is not None and end is not None and _date(start, "expected_start") > _date(end, "expected_end"):
            raise ValueError("Cadence expected_start must not follow expected_end.")
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
        if cursor == last:
            break
        try:
            cursor = _next_date(cursor, parsed["frequency"])
        except (ValueError, OverflowError) as exc:
            raise ValueError("Cadence dates are off-grid for the declared frequency.") from exc
    if expected != len(unique) + missing:
        raise ValueError("Cadence dates are off-grid for the declared frequency.")
    receipt = {
        **parsed, "start_date": first.isoformat(), "end_date": last.isoformat(),
        "observed_count": len(observed), "expected_count": expected,
        "missing_count": missing, "missing_preview": preview,
    }
    if parsed["version"] == 2:
        receipt.update(_boundary_receipts(parsed, first, last, expected))
    return receipt


def _boundary_receipts(
    declaration: Mapping[str, Any], first: date, last: date, internal_count: int,
) -> dict[str, Any]:
    """Count only explicitly expected leading/trailing slots; keep v1 internal receipts unchanged."""
    frequency = declaration["frequency"]
    start_raw, end_raw = declaration["expected_start"], declaration["expected_end"]
    leading = trailing = 0
    preview: list[str] = []

    if start_raw is not None:
        start = _date(start_raw, "expected_start")
        if start > first:
            raise ValueError("Cadence expected_start is after the first source observation.")
        cursor = start
        while cursor < first:
            leading += 1
            if leading + internal_count > _MAX_PERIODS:
                raise ValueError(f"Cadence expected window exceeds the {_MAX_PERIODS} period safety limit.")
            if len(preview) < _PREVIEW_LIMIT:
                preview.append(cursor.isoformat())
            try:
                cursor = _next_date(cursor, frequency)
            except (ValueError, OverflowError) as exc:
                raise ValueError("Cadence expected_start is off-grid from the source dates.") from exc
        if cursor != first:
            raise ValueError("Cadence expected_start is off-grid from the source dates.")

    if end_raw is not None:
        end = _date(end_raw, "expected_end")
        if end < last:
            raise ValueError("Cadence expected_end is before the last source observation.")
        cursor = last
        while cursor < end:
            if internal_count + leading + trailing >= _MAX_PERIODS:
                raise ValueError(f"Cadence expected window exceeds the {_MAX_PERIODS} period safety limit.")
            try:
                cursor = _next_date(cursor, frequency)
            except (ValueError, OverflowError) as exc:
                raise ValueError("Cadence expected_end is off-grid from the source dates.") from exc
            if cursor > end:
                raise ValueError("Cadence expected_end is off-grid from the source dates.")
            trailing += 1
            if len(preview) < _PREVIEW_LIMIT:
                preview.append(cursor.isoformat())

    return {
        "expected_window_count": internal_count + leading + trailing,
        "leading_missing_count": leading,
        "trailing_missing_count": trailing,
        "boundary_missing_preview": preview,
    }


def parse_cadence_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or CADENCE_CONTRACT_KEY not in usermeta:
        return None
    raw = usermeta[CADENCE_CONTRACT_KEY]
    if not isinstance(raw, Mapping):
        raise ValueError("usermeta.cadence_contract must be an object.")
    version = raw.get("version")
    if type(version) is not int or version not in (1, 2):
        raise ValueError("Cadence contract version must equal 1 or 2.")
    inputs = _INPUTS if version == 1 else _INPUTS_V2
    receipt_fields = _RECEIPTS if version == 1 else _RECEIPTS | _BOUNDARY_RECEIPTS
    if set(raw) != inputs | receipt_fields:
        raise ValueError(f"usermeta.cadence_contract requires exactly the closed v{version} fields.")
    declaration = validate_cadence_declaration({key: raw[key] for key in inputs})
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
    if version == 2:
        for key in ("expected_window_count", "leading_missing_count", "trailing_missing_count"):
            minimum = 1 if key == "expected_window_count" else 0
            if type(raw[key]) is not int or raw[key] < minimum:
                raise ValueError(f"Cadence {key} must be an integer >= {minimum}.")
        boundary_preview = raw["boundary_missing_preview"]
        if (not isinstance(boundary_preview, list) or len(boundary_preview) > _PREVIEW_LIMIT
                or any(not isinstance(day, str) for day in boundary_preview)):
            raise ValueError("Cadence boundary_missing_preview must be an array of at most five date strings.")
        for day in boundary_preview:
            _date(day, "boundary_missing_preview")
        if len(boundary_preview) > raw["leading_missing_count"] + raw["trailing_missing_count"]:
            raise ValueError("Cadence boundary preview exceeds missing boundary count.")
    return {**declaration, **{key: raw[key] for key in receipt_fields}}


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


def cadence_boundary_outcome(receipt: Mapping[str, Any]) -> tuple[str, str]:
    """Review/block explicitly missing leading or trailing periods independently of interior gaps."""
    if receipt["version"] != 2:
        raise ValueError("Boundary checks require a v2 cadence receipt.")
    leading, trailing = receipt["leading_missing_count"], receipt["trailing_missing_count"]
    total = leading + trailing
    if total == 0:
        return "PASS", "All explicitly expected leading/trailing cadence periods are present."
    severity = "FAIL" if receipt["require_complete"] else "WARN"
    bounds = f"{receipt['expected_start'] or receipt['start_date']} to {receipt['expected_end'] or receipt['end_date']}"
    return severity, (
        f"Cadence boundary gap: {leading} leading and {trailing} trailing "
        f"{receipt['frequency']} period(s) missing in expected window {bounds}; "
        f"first missing: {', '.join(receipt['boundary_missing_preview'])}."
    )
