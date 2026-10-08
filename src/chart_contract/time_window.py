"""Explicit time-window comparability contracts."""

from __future__ import annotations

import calendar
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any

TIME_WINDOW_CONTRACT_KEY = "time_window_contract"
TIME_WINDOW_CONTRACT_VERSION = 1
WINDOW_KINDS = {"calendar", "rolling"}
CALENDAR_GRANULARITIES = {"day", "week", "month", "quarter", "year"}


@dataclass(frozen=True, slots=True)
class TimeWindowSummary:
    window_kind: str
    window_granularity: str | None
    baseline_start: str
    baseline_end: str
    target_start: str
    target_end: str
    baseline_complete: bool
    target_complete: bool
    baseline_days: int
    target_days: int

    def to_dict(self) -> dict[str, Any]:
        return {"version": TIME_WINDOW_CONTRACT_VERSION, **asdict(self)}


def time_window_declaration(chart: Any) -> dict[str, Any] | None:
    names = (
        "window_kind",
        "window_granularity",
        "baseline_start",
        "baseline_end",
        "target_start",
        "target_end",
        "baseline_complete",
        "target_complete",
    )
    values = tuple(getattr(chart, name, None) for name in names)
    if all(value is None for value in values):
        return None
    return {name: value for name, value in zip(names, values)}


def build_time_window_summary(
    *,
    window_kind: Any,
    window_granularity: Any,
    baseline_start: Any,
    baseline_end: Any,
    target_start: Any,
    target_end: Any,
    baseline_complete: Any,
    target_complete: Any,
) -> TimeWindowSummary:
    kind = _window_kind(window_kind)
    granularity = _granularity(window_granularity, kind)
    b_start = _iso_date(baseline_start, "baseline_start")
    b_end = _iso_date(baseline_end, "baseline_end")
    t_start = _iso_date(target_start, "target_start")
    t_end = _iso_date(target_end, "target_end")
    b_complete = _boolean(baseline_complete, "baseline_complete")
    t_complete = _boolean(target_complete, "target_complete")

    if b_start > b_end:
        raise ValueError("baseline_start must be on or before baseline_end.")
    if t_start > t_end:
        raise ValueError("target_start must be on or before target_end.")

    if kind == "calendar":
        if b_complete:
            _validate_complete_calendar_window(b_start, b_end, granularity, "baseline")
        if t_complete:
            _validate_complete_calendar_window(t_start, t_end, granularity, "target")

    return TimeWindowSummary(
        window_kind=kind,
        window_granularity=granularity,
        baseline_start=b_start.isoformat(),
        baseline_end=b_end.isoformat(),
        target_start=t_start.isoformat(),
        target_end=t_end.isoformat(),
        baseline_complete=b_complete,
        target_complete=t_complete,
        baseline_days=(b_end - b_start).days + 1,
        target_days=(t_end - t_start).days + 1,
    )


def parse_time_window_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or TIME_WINDOW_CONTRACT_KEY not in usermeta:
        return None

    contract = usermeta.get(TIME_WINDOW_CONTRACT_KEY)
    if not isinstance(contract, Mapping):
        raise ValueError("usermeta.time_window_contract must be an object.")

    expected = {
        "version",
        "window_kind",
        "window_granularity",
        "baseline_start",
        "baseline_end",
        "target_start",
        "target_end",
        "baseline_complete",
        "target_complete",
        "baseline_days",
        "target_days",
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
            "usermeta.time_window_contract must use the exact v1 field set"
            + (" (" + "; ".join(details) + ")" if details else "")
            + "."
        )
    if contract.get("version") != TIME_WINDOW_CONTRACT_VERSION:
        raise ValueError(
            f"usermeta.time_window_contract.version must equal {TIME_WINDOW_CONTRACT_VERSION}."
        )

    summary = build_time_window_summary(
        window_kind=contract.get("window_kind"),
        window_granularity=contract.get("window_granularity"),
        baseline_start=contract.get("baseline_start"),
        baseline_end=contract.get("baseline_end"),
        target_start=contract.get("target_start"),
        target_end=contract.get("target_end"),
        baseline_complete=contract.get("baseline_complete"),
        target_complete=contract.get("target_complete"),
    ).to_dict()

    for field in ("baseline_days", "target_days"):
        value = contract.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"usermeta.time_window_contract.{field} must be a positive integer.")
        summary[field] = value
    return summary


def _window_kind(value: Any) -> str:
    if not isinstance(value, str) or value not in WINDOW_KINDS:
        raise ValueError("window_kind must be 'calendar' or 'rolling'.")
    return value


def _granularity(value: Any, kind: str) -> str | None:
    if kind == "rolling":
        if value is not None:
            raise ValueError("rolling windows require window_granularity=None.")
        return None
    if not isinstance(value, str) or value not in CALENDAR_GRANULARITIES:
        raise ValueError(
            "calendar windows require granularity day, week, month, quarter, or year."
        )
    return value


def _iso_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO YYYY-MM-DD string.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO YYYY-MM-DD string.") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{field} must use canonical ISO YYYY-MM-DD form.")
    return parsed


def _boolean(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be boolean.")
    return value


def _validate_complete_calendar_window(
    start: date,
    end: date,
    granularity: str | None,
    label: str,
) -> None:
    if granularity == "day":
        expected_start = start
        expected_end = start
    elif granularity == "week":
        expected_start = start
        expected_end = start + timedelta(days=6)
    elif granularity == "month":
        expected_start = start.replace(day=1)
        expected_end = start.replace(day=calendar.monthrange(start.year, start.month)[1])
    elif granularity == "quarter":
        quarter_start_month = ((start.month - 1) // 3) * 3 + 1
        expected_start = date(start.year, quarter_start_month, 1)
        end_month = quarter_start_month + 2
        expected_end = date(
            start.year,
            end_month,
            calendar.monthrange(start.year, end_month)[1],
        )
    elif granularity == "year":
        expected_start = date(start.year, 1, 1)
        expected_end = date(start.year, 12, 31)
    else:
        raise ValueError("Unsupported calendar granularity.")

    if start != expected_start or end != expected_end:
        raise ValueError(
            f"{label} window marked complete does not span one complete calendar "
            f"{granularity}: {start.isoformat()} to {end.isoformat()}."
        )
