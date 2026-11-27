"""Closed, opt-in completeness receipts for grouped trend period grids.

A globally complete timeline can still omit a single subgroup-week. The
operator supplies the group inventory; nothing is inferred as a required group.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

import pandas as pd

from .cadence import FREQUENCIES, _date, _next_date

GROUP_CADENCE_KEY = "group_cadence_contract"
_INPUTS = {
    "version", "date_field", "group_field", "frequency", "require_complete",
    "expected_groups", "expected_start", "expected_end",
}
_RECEIPTS = {
    "start_date", "end_date", "observed_count", "expected_period_count",
    "expected_cell_count", "missing_count", "missing_preview",
}
_MAX_CELLS = 10000
_MAX_GROUPS = 32
_PREVIEW = 5


def chart_group_cadence_declaration(chart: Any) -> dict[str, Any] | None:
    groups = getattr(chart, "cadence_expected_groups", None)
    if groups is None:
        return None
    return {
        "version": 1,
        "date_field": getattr(chart, "x", None),
        "group_field": getattr(chart, "group", None),
        "frequency": getattr(chart, "cadence_frequency", None),
        "require_complete": getattr(chart, "cadence_require_complete", None),
        "expected_groups": groups,
        "expected_start": getattr(chart, "cadence_expected_start", None),
        "expected_end": getattr(chart, "cadence_expected_end", None),
    }


def validate_group_cadence_declaration(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) != _INPUTS:
        raise ValueError("Group cadence requires exactly the closed v1 input fields.")
    if type(raw["version"]) is not int or raw["version"] != 1:
        raise ValueError("Group cadence contract version must equal 1.")
    date_field, group_field = raw["date_field"], raw["group_field"]
    if (not isinstance(date_field, str) or not date_field.strip()
            or not isinstance(group_field, str) or not group_field.strip()
            or date_field == group_field):
        raise ValueError("Group cadence requires distinct non-empty date_field and group_field.")
    if not isinstance(raw["frequency"], str) or raw["frequency"] not in FREQUENCIES:
        raise ValueError("Group cadence frequency must be daily, weekly, or monthly.")
    if type(raw["require_complete"]) is not bool:
        raise ValueError("Group cadence require_complete must be a boolean.")

    groups = raw["expected_groups"]
    if (not isinstance(groups, (list, tuple)) or not 1 <= len(groups) <= _MAX_GROUPS
            or any(not isinstance(name, str) or not name.strip() for name in groups)
            or len(groups) != len(set(groups))):
        raise ValueError("Group cadence expected_groups must contain 1-32 unique non-empty strings.")

    start, end = raw["expected_start"], raw["expected_end"]
    for key, value in (("expected_start", start), ("expected_end", end)):
        if value is not None:
            day = _date(value, key)
            if raw["frequency"] == "monthly" and day.day != 1:
                raise ValueError("Group cadence monthly boundaries must be first-of-month dates.")
    if start is not None and end is not None and _date(start, "expected_start") > _date(end, "expected_end"):
        raise ValueError("Group cadence expected_start must not follow expected_end.")

    return {**raw, "expected_groups": list(groups)}


def _periods(start: date, end: date, frequency: str, group_count: int) -> list[date]:
    periods = []
    cursor = start
    while cursor <= end:
        if (len(periods) + 1) * group_count > _MAX_CELLS:
            raise ValueError(f"Group cadence grid exceeds the {_MAX_CELLS} cell safety limit.")
        periods.append(cursor)
        if cursor == end:
            break
        try:
            cursor = _next_date(cursor, frequency)
        except (ValueError, OverflowError) as exc:
            raise ValueError("Group cadence end date is off-grid.") from exc
    if not periods or periods[-1] != end:
        raise ValueError("Group cadence end date is off-grid from the start date.")
    return periods


def build_group_cadence_receipt(frame: pd.DataFrame, declaration: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute a complete date × declared group grid without filling data."""
    parsed = validate_group_cadence_declaration(declaration)
    if not isinstance(frame, pd.DataFrame):
        raise ValueError("Group cadence requires reconstructable DataFrame source evidence.")
    date_field, group_field = parsed["date_field"], parsed["group_field"]
    if date_field not in frame or group_field not in frame:
        raise ValueError("Group cadence source is missing the declared date or group field.")
    if frame.empty:
        raise ValueError("Group cadence requires at least one original observation.")

    expected_groups = parsed["expected_groups"]
    observed: set[tuple[date, str]] = set()
    for index, (raw_date, raw_group) in enumerate(
        frame[[date_field, group_field]].itertuples(index=False, name=None), 1
    ):
        day = _date(raw_date, f"row {index} date")
        if parsed["frequency"] == "monthly" and day.day != 1:
            raise ValueError("Monthly group cadence requires first-of-month source dates.")
        if not isinstance(raw_group, str) or raw_group not in expected_groups:
            raise ValueError(f"Group cadence row {index} has an undeclared or invalid group.")
        key = (day, raw_group)
        if key in observed:
            raise ValueError("Group cadence has duplicate (date, group) source rows; aggregate upstream.")
        observed.add(key)

    dates = [key[0] for key in observed]
    first, last = min(dates), max(dates)
    start = _date(parsed["expected_start"], "expected_start") if parsed["expected_start"] is not None else first
    end = _date(parsed["expected_end"], "expected_end") if parsed["expected_end"] is not None else last
    if start > first or end < last:
        raise ValueError("Group cadence declared window must contain all source dates.")

    periods = _periods(start, end, parsed["frequency"], len(expected_groups))
    if not {day for day in dates}.issubset(periods):
        raise ValueError("Group cadence source dates are off-grid for the declared window/frequency.")

    missing_count = 0
    preview: list[dict[str, str]] = []
    for day in periods:
        for group in expected_groups:
            if (day, group) not in observed:
                missing_count += 1
                if len(preview) < _PREVIEW:
                    preview.append({"date": day.isoformat(), "group": group})

    expected_cells = len(periods) * len(expected_groups)
    if len(observed) + missing_count != expected_cells:
        raise ValueError("Group cadence source observations do not match the declared grid.")

    return {
        **parsed, "start_date": start.isoformat(), "end_date": end.isoformat(),
        "observed_count": len(observed), "expected_period_count": len(periods),
        "expected_cell_count": expected_cells, "missing_count": missing_count,
        "missing_preview": preview,
    }


def parse_group_cadence_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    meta = spec.get("usermeta")
    if not isinstance(meta, Mapping) or GROUP_CADENCE_KEY not in meta:
        return None
    raw = meta[GROUP_CADENCE_KEY]
    if not isinstance(raw, Mapping) or set(raw) != _INPUTS | _RECEIPTS:
        raise ValueError("usermeta.group_cadence_contract requires exactly the closed v1 fields.")
    declared = validate_group_cadence_declaration({k: raw[k] for k in _INPUTS})
    start, end = _date(raw["start_date"], "start_date"), _date(raw["end_date"], "end_date")
    if start > end:
        raise ValueError("Group cadence start_date cannot follow end_date.")
    for key in ("observed_count", "expected_period_count", "expected_cell_count", "missing_count"):
        minimum = 0 if key == "missing_count" else 1
        if type(raw[key]) is not int or raw[key] < minimum:
            raise ValueError(f"Group cadence {key} must be an integer >= {minimum}.")
    if raw["expected_period_count"] * len(declared["expected_groups"]) != raw["expected_cell_count"]:
        raise ValueError("Group cadence expected_cell_count must match periods × groups.")
    if raw["observed_count"] + raw["missing_count"] != raw["expected_cell_count"]:
        raise ValueError("Group cadence observed and missing counts must account for every cell.")
    preview = raw["missing_preview"]
    if not isinstance(preview, list) or len(preview) > _PREVIEW or len(preview) > raw["missing_count"]:
        raise ValueError("Group cadence missing_preview must contain at most five missing cells.")
    for cell in preview:
        if (not isinstance(cell, Mapping) or set(cell) != {"date", "group"}
                or cell["group"] not in declared["expected_groups"]):
            raise ValueError("Group cadence missing_preview contains an invalid cell.")
        _date(cell["date"], "missing_preview date")
    return {**declared, **{k: raw[k] for k in _RECEIPTS}}


def group_cadence_outcome(receipt: Mapping[str, Any]) -> tuple[str, str]:
    missing, total = receipt["missing_count"], receipt["expected_cell_count"]
    if not missing:
        return "PASS", f"Grouped cadence complete: all {total} expected date × subgroup cells are present."
    severity = "FAIL" if receipt["require_complete"] else "WARN"
    preview = ", ".join(f"{cell['group']} @ {cell['date']}" for cell in receipt["missing_preview"])
    return severity, (
        f"Grouped cadence gap: {missing} of {total} expected date × subgroup cells missing "
        f"from {receipt['start_date']} through {receipt['end_date']}; first missing: {preview}."
    )
