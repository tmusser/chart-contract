"""Explicit observed/structural-zero/missing/suppressed metric value semantics."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping
from typing import Any

import pandas as pd

OBSERVATION_STATUS_KEY = "observation_status_contract"
OBSERVATION_STATUS_VERSION = 1
OBSERVATION_STATUS_INTENTS = {"trend", "rank", "compare"}
OBSERVATION_STATES = ("observed", "structural_zero", "missing", "suppressed")


def chart_observation_declaration(chart: Any) -> dict[str, Any] | None:
    field = getattr(chart, "observation_status_field", None)
    if field is None:
        return None
    return {"version": OBSERVATION_STATUS_VERSION, "metric_field": chart.y, "status_field": field}


def parse_observation_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    meta = spec.get("usermeta")
    if not isinstance(meta, Mapping) or OBSERVATION_STATUS_KEY not in meta:
        return None
    raw = meta.get(OBSERVATION_STATUS_KEY)
    if not isinstance(raw, Mapping):
        raise ValueError("usermeta.observation_status_contract must be an object.")
    required = {"version", "metric_field", "status_field", "counts"}
    if set(raw) != required:
        raise ValueError("usermeta.observation_status_contract must use the exact v1 field set.")
    if type(raw.get("version")) is not int or raw["version"] != OBSERVATION_STATUS_VERSION:
        raise ValueError("observation status contract version must equal 1.")
    for field in ("metric_field", "status_field"):
        if not isinstance(raw.get(field), str) or not raw[field].strip():
            raise ValueError(f"observation status {field} must be a non-empty string.")
    if raw["metric_field"] == raw["status_field"]:
        raise ValueError("observation status field must differ from metric field.")
    counts = raw["counts"]
    if not isinstance(counts, Mapping) or set(counts) != set(OBSERVATION_STATES):
        raise ValueError("observation status counts must declare exactly the four supported states.")
    for key in OBSERVATION_STATES:
        if type(counts[key]) is not int or counts[key] < 0:
            raise ValueError(f"observation status count {key} must be a non-negative integer.")
    return {
        "version": OBSERVATION_STATUS_VERSION,
        "metric_field": raw["metric_field"],
        "status_field": raw["status_field"],
        "counts": {key: counts[key] for key in OBSERVATION_STATES},
    }


def build_observation_contract(
    frame: pd.DataFrame, *, metric_field: str, status_field: str
) -> dict[str, Any]:
    if not isinstance(metric_field, str) or not metric_field.strip():
        raise ValueError("observation status metric_field must be a non-empty string.")
    if not isinstance(status_field, str) or not status_field.strip():
        raise ValueError("observation status status_field must be a non-empty string.")
    if metric_field == status_field:
        raise ValueError("observation status field must differ from metric field.")
    ok, message, counts = observation_evidence_status(
        frame, metric_field=metric_field, status_field=status_field
    )
    if not ok:
        raise ValueError(message)
    return {
        "version": OBSERVATION_STATUS_VERSION,
        "metric_field": metric_field,
        "status_field": status_field,
        "counts": counts,
    }


def observation_evidence_status(
    frame: pd.DataFrame, *, metric_field: str, status_field: str
) -> tuple[bool, str, dict[str, int]]:
    """Validate each row without rescaling, imputing, dropping, or inferring status."""

    missing = [field for field in (metric_field, status_field) if field not in frame.columns]
    if missing:
        return False, "Observation status evidence is missing field(s): " + ", ".join(missing), {}
    counts: Counter[str] = Counter()
    for index, (state, value) in enumerate(
        zip(frame[status_field].tolist(), frame[metric_field].tolist()), start=1
    ):
        if not isinstance(state, str) or state not in OBSERVATION_STATES:
            return False, (
                f"Observation status row {index} has invalid state {state!r}; "
                "expected observed, structural_zero, missing, or suppressed."
            ), {}
        counts[state] += 1
        try:
            absent = bool(pd.isna(value))
        except (TypeError, ValueError):
            return False, f"Observation status row {index} contains an unsupported metric value.", {}
        if state in {"missing", "suppressed"}:
            if not absent:
                return False, (
                    f"Observation status row {index} declares {state} but contains a metric value; "
                    "missing/suppressed values must be null, never zero-filled."
                ), {}
            continue
        if absent or isinstance(value, bool):
            return False, (
                f"Observation status row {index} declares {state} but lacks a finite numeric value."
            ), {}
        try:
            numeric = float(value)
        except (ValueError, TypeError, OverflowError):
            return False, f"Observation status row {index} must contain a numeric value.", {}
        if not math.isfinite(numeric):
            return False, f"Observation status row {index} must contain a finite value.", {}
        if state == "structural_zero" and numeric != 0:
            return False, (
                f"Observation status row {index} declares structural_zero but the value is not zero."
            ), {}
    result = {key: counts.get(key, 0) for key in OBSERVATION_STATES}
    return True, (
        "Observation status rows are consistent: "
        + ", ".join(f"{key}={result[key]}" for key in OBSERVATION_STATES)
        + "."
    ), result
