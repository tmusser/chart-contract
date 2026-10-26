"""Bounded, deterministic subgroup composition / Simpson-reversal receipts.

This proves arithmetic on supplied two-period subgroup counts, not causality.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from numbers import Real
from typing import Any

import pandas as pd

COMPOSITION_KEY = "composition_contract"
COMPOSITION_INTENTS = {"compare"}
_INPUTS = (
    "version", "period_field", "group_field", "metric_field",
    "numerator_field", "denominator_field", "baseline_value", "target_value",
    "multiplier", "tolerance",
)
_RECEIPTS = (
    "group_count", "baseline_numerator", "baseline_denominator",
    "target_numerator", "target_denominator", "baseline_overall",
    "target_overall", "subgroup_direction", "aggregate_direction", "reversal",
)


def composition_declaration(chart: Any) -> dict[str, Any] | None:
    before = getattr(chart, "composition_baseline_value", None)
    after = getattr(chart, "composition_target_value", None)
    if before is None and after is None:
        return None
    return {
        "version": 1,
        "period_field": getattr(chart, "x", None),
        "group_field": getattr(chart, "group", None),
        "metric_field": getattr(chart, "y", None),
        "numerator_field": getattr(chart, "numerator_value_field", None),
        "denominator_field": getattr(chart, "denominator_value_field", None),
        "baseline_value": before,
        "target_value": after,
        "multiplier": (
            getattr(chart, "ratio_multiplier", None)
            if getattr(chart, "ratio_multiplier", None) is not None else 1.0
        ),
        "tolerance": (
            getattr(chart, "ratio_tolerance", None)
            if getattr(chart, "ratio_tolerance", None) is not None else 1e-9
        ),
    }


def _finite(value: Any, name: str, *, lower: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"Composition {name} must be finite numeric evidence.")
    number = float(value)
    if lower is not None and number < lower:
        raise ValueError(f"Composition {name} must be at least {lower:g}.")
    return number


def _inputs(values: Mapping[str, Any]) -> dict[str, Any]:
    if set(values) != set(_INPUTS):
        raise ValueError("Composition declaration must use exactly the closed v1 input fields.")
    if type(values["version"]) is not int or values["version"] != 1:
        raise ValueError("Composition version must equal 1.")
    fields = ("period_field", "group_field", "metric_field", "numerator_field", "denominator_field")
    result = dict(values)
    for key in fields + ("baseline_value", "target_value"):
        item = result[key]
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"Composition {key} must be a non-empty string.")
    if len({result[k] for k in fields}) != len(fields):
        raise ValueError("Composition period, subgroup, metric, and count fields must be distinct.")
    if result["baseline_value"] == result["target_value"]:
        raise ValueError("Composition baseline and target values must differ.")
    result["multiplier"] = _finite(result["multiplier"], "multiplier")
    if result["multiplier"] <= 0:
        raise ValueError("Composition multiplier must be positive.")
    result["tolerance"] = _finite(result["tolerance"], "tolerance", lower=0.0)
    return result


def _direction(before: float, after: float) -> str:
    if math.isclose(before, after, rel_tol=0.0, abs_tol=1e-12):
        return "flat"
    return "up" if after > before else "down"


def build_composition_receipt(frame: pd.DataFrame, declaration: Mapping[str, Any]) -> dict[str, Any]:
    """Validate full subgroup-by-period evidence and recompute the weighted aggregate."""
    meta = _inputs(declaration)
    fields = (
        meta["period_field"], meta["group_field"], meta["metric_field"],
        meta["numerator_field"], meta["denominator_field"],
    )
    missing = [field for field in fields if field not in frame.columns]
    if missing:
        raise ValueError("Composition evidence missing field(s): " + ", ".join(missing))
    if frame.empty:
        raise ValueError("Composition evidence cannot be empty.")
    before, after = meta["baseline_value"], meta["target_value"]
    observations: dict[tuple[str, str], tuple[float, float]] = {}
    groups: set[str] = set()
    for position, (period, group, displayed, numerator, denominator) in enumerate(
        frame[list(fields)].itertuples(index=False, name=None), start=1
    ):
        if not isinstance(period, str) or period not in {before, after}:
            raise ValueError(f"Composition row {position} has an undeclared period.")
        if not isinstance(group, str) or not group.strip():
            raise ValueError(f"Composition row {position} has a missing or invalid subgroup.")
        metric = _finite(displayed, f"row {position} metric")
        num = _finite(numerator, f"row {position} numerator", lower=0.0)
        den = _finite(denominator, f"row {position} denominator")
        if den <= 0:
            raise ValueError(f"Composition row {position} has a zero or negative denominator.")
        if num > den:
            raise ValueError(f"Composition row {position} numerator exceeds denominator (proportion contract).")
        expected = num / den * meta["multiplier"]
        if not math.isfinite(expected) or not math.isclose(
            metric, expected, rel_tol=0.0, abs_tol=meta["tolerance"]
        ):
            raise ValueError(
                f"Composition row {position} has inconsistent displayed rate: "
                f"observed {metric:g} vs computed {expected:g}."
            )
        key = (period, group)
        if key in observations:
            raise ValueError(f"Composition evidence contains duplicate period/subgroup key {key!r}.")
        observations[key] = (num, den)
        groups.add(group)

    if len(groups) < 2:
        raise ValueError("Composition reversal audit requires at least two subgroups.")
    if len(observations) != 2 * len(groups) or any(
        (period, group) not in observations
        for period in (before, after) for group in groups
    ):
        raise ValueError("Composition requires identical, complete subgroup sets in both periods.")

    directions = {
        _direction(
            observations[(before, group)][0] / observations[(before, group)][1],
            observations[(after, group)][0] / observations[(after, group)][1],
        )
        for group in groups
    }
    subgroup_direction = next(iter(directions)) if len(directions) == 1 else "mixed"
    totals = {}
    for period in (before, after):
        numerator_total = math.fsum(observations[(period, group)][0] for group in groups)
        denominator_total = math.fsum(observations[(period, group)][1] for group in groups)
        if not math.isfinite(numerator_total) or not math.isfinite(denominator_total):
            raise ValueError("Composition totals must remain finite.")
        totals[period] = (numerator_total, denominator_total)
    bnum, bden = totals[before]
    tnum, tden = totals[after]
    overall_before, overall_after = bnum / bden, tnum / tden
    aggregate_direction = _direction(overall_before, overall_after)
    reversal = subgroup_direction in {"up", "down"} and aggregate_direction in {"up", "down"} and subgroup_direction != aggregate_direction

    return {
        **meta,
        "group_count": len(groups),
        "baseline_numerator": bnum,
        "baseline_denominator": bden,
        "target_numerator": tnum,
        "target_denominator": tden,
        "baseline_overall": overall_before * meta["multiplier"],
        "target_overall": overall_after * meta["multiplier"],
        "subgroup_direction": subgroup_direction,
        "aggregate_direction": aggregate_direction,
        "reversal": reversal,
    }


def parse_composition_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or COMPOSITION_KEY not in usermeta:
        return None
    raw = usermeta[COMPOSITION_KEY]
    if not isinstance(raw, Mapping) or set(raw) != set(_INPUTS) | set(_RECEIPTS):
        raise ValueError("usermeta.composition_contract must use the exact closed v1 fields.")
    meta = _inputs({name: raw[name] for name in _INPUTS})
    for field in ("group_count",):
        value = raw[field]
        if type(value) is not int or value < 2:
            raise ValueError("Composition group_count must be an integer >= 2.")
    for field in ("baseline_numerator", "baseline_denominator", "target_numerator",
                  "target_denominator", "baseline_overall", "target_overall"):
        _finite(raw[field], field, lower=0.0)
    for field in ("subgroup_direction", "aggregate_direction"):
        if raw[field] not in {"up", "down", "flat", "mixed"}:
            raise ValueError(f"Composition {field} has unsupported direction.")
    if type(raw["reversal"]) is not bool:
        raise ValueError("Composition reversal receipt must be a boolean.")
    return {**raw, **meta}


def receipts_match(saved: Mapping[str, Any], actual: Mapping[str, Any]) -> bool:
    for name in _RECEIPTS:
        old, new = saved[name], actual[name]
        if name in {
            "baseline_numerator", "baseline_denominator", "target_numerator",
            "target_denominator", "baseline_overall", "target_overall",
        }:
            if not math.isclose(old, new, rel_tol=1e-12, abs_tol=1e-12):
                return False
        elif old != new:
            return False
    return True
