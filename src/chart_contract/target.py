"""Explicit scalar target-threshold semantics for analytical metrics."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

TARGET_CONTRACT_KEY = "target_contract"
TARGET_CONTRACT_VERSION = 1
TARGET_INTENTS = {"trend", "compare"}
TARGET_OPERATORS = {"at_least", "at_most", "equal"}

_MET_PATTERNS = (
    re.compile(r"\bmet\s+(?:the\s+)?target\b", re.IGNORECASE),
    re.compile(r"\bmeets?\s+(?:the\s+)?target\b", re.IGNORECASE),
    re.compile(r"\bmeeting\s+(?:the\s+)?target\b", re.IGNORECASE),
    re.compile(r"\bhit\s+(?:the\s+)?target\b", re.IGNORECASE),
    re.compile(r"\bhits\s+(?:the\s+)?target\b", re.IGNORECASE),
    re.compile(r"\breached\s+(?:the\s+)?target\b", re.IGNORECASE),
    re.compile(r"\btarget\s+(?:was|is)\s+met\b", re.IGNORECASE),
)
_MISSED_PATTERNS = (
    re.compile(r"\bmissed\s+(?:the\s+)?target\b", re.IGNORECASE),
    re.compile(r"\bmisses\s+(?:the\s+)?target\b", re.IGNORECASE),
    re.compile(r"\bmissing\s+(?:the\s+)?target\b", re.IGNORECASE),
    re.compile(r"\btarget\s+(?:was|is)\s+missed\b", re.IGNORECASE),
)


@dataclass(frozen=True, slots=True)
class TargetSummary:
    metric_field: str
    selector_field: str
    selector_value: str | int | float
    target_value: float
    operator: str
    tolerance: float
    observed_value: float
    target_gap: float
    target_met: bool

    def to_dict(self) -> dict[str, Any]:
        return {"version": TARGET_CONTRACT_VERSION, **asdict(self)}


def target_declaration(chart: Any) -> dict[str, Any] | None:
    values = (
        getattr(chart, "metric_target", None),
        getattr(chart, "target_operator", None),
        getattr(chart, "target_selector_field", None),
        getattr(chart, "target_selector_value", None),
        getattr(chart, "target_tolerance", None),
    )
    if all(value is None for value in values):
        return None
    return {
        "metric_field": getattr(chart, "y", None),
        "selector_field": getattr(chart, "target_selector_field", None),
        "selector_value": getattr(chart, "target_selector_value", None),
        "target_value": getattr(chart, "metric_target", None),
        "operator": getattr(chart, "target_operator", None),
        "tolerance": getattr(chart, "target_tolerance", None),
    }


def build_target_summary(
    frame: pd.DataFrame,
    *,
    metric_field: Any,
    selector_field: Any,
    selector_value: Any,
    target_value: Any,
    operator: Any,
    tolerance: Any,
) -> TargetSummary:
    metric = _required_string(metric_field, "metric_field")
    selector = _required_string(selector_field, "selector_field")
    selected = _selector_value(selector_value, "selector_value")
    target = _finite_number(target_value, "target_value")
    op = _operator(operator)
    tol = 0.0 if tolerance is None else _nonnegative_number(tolerance, "tolerance")

    if selector not in frame.columns:
        raise ValueError(f"Target selector field {selector!r} is missing from the data.")
    if metric not in frame.columns:
        raise ValueError(f"Target metric field {metric!r} is missing from the data.")

    rows = frame.loc[frame[selector] == selected]
    if len(rows) != 1:
        raise ValueError(
            f"Target selector {selector}={selected!r} matched {len(rows)} rows; "
            "exactly one is required."
        )

    raw = rows.iloc[0][metric]
    if pd.isna(raw):
        raise ValueError("Selected target observation metric value must be non-null.")
    if isinstance(raw, bool):
        raise ValueError("Selected target observation metric value must be numeric, not boolean.")
    try:
        observed = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("Selected target observation metric value must be numeric.") from exc
    if not math.isfinite(observed):
        raise ValueError("Selected target observation metric value must be finite.")

    met = target_status(observed, target, operator=op, tolerance=tol)
    return TargetSummary(
        metric_field=metric,
        selector_field=selector,
        selector_value=selected,
        target_value=target,
        operator=op,
        tolerance=tol,
        observed_value=observed,
        target_gap=observed - target,
        target_met=met,
    )


def parse_target_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or TARGET_CONTRACT_KEY not in usermeta:
        return None

    contract = usermeta.get(TARGET_CONTRACT_KEY)
    if not isinstance(contract, Mapping):
        raise ValueError("usermeta.target_contract must be an object.")

    expected = {
        "version",
        "metric_field",
        "selector_field",
        "selector_value",
        "target_value",
        "operator",
        "tolerance",
        "observed_value",
        "target_gap",
        "target_met",
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
            "usermeta.target_contract must use the exact v1 field set"
            + (" (" + "; ".join(details) + ")" if details else "")
            + "."
        )

    if contract.get("version") != TARGET_CONTRACT_VERSION:
        raise ValueError(
            f"usermeta.target_contract.version must equal {TARGET_CONTRACT_VERSION}."
        )

    met = contract.get("target_met")
    if not isinstance(met, bool):
        raise ValueError("usermeta.target_contract.target_met must be boolean.")

    return {
        "version": TARGET_CONTRACT_VERSION,
        "metric_field": _required_string(contract.get("metric_field"), "metric_field"),
        "selector_field": _required_string(contract.get("selector_field"), "selector_field"),
        "selector_value": _selector_value(contract.get("selector_value"), "selector_value"),
        "target_value": _finite_number(contract.get("target_value"), "target_value"),
        "operator": _operator(contract.get("operator")),
        "tolerance": _nonnegative_number(contract.get("tolerance"), "tolerance"),
        "observed_value": _finite_number(contract.get("observed_value"), "observed_value"),
        "target_gap": _finite_number(contract.get("target_gap"), "target_gap"),
        "target_met": met,
    }


def target_status(
    observed: float,
    target: float,
    *,
    operator: str,
    tolerance: float,
) -> bool:
    if operator == "at_least":
        return observed >= target - tolerance
    if operator == "at_most":
        return observed <= target + tolerance
    if operator == "equal":
        return math.isclose(observed, target, rel_tol=0.0, abs_tol=tolerance)
    raise ValueError(f"Unsupported target operator: {operator!r}.")


def target_receipts_match(
    contract: Mapping[str, Any],
    summary: TargetSummary,
) -> bool:
    return (
        contract["metric_field"] == summary.metric_field
        and contract["selector_field"] == summary.selector_field
        and contract["selector_value"] == summary.selector_value
        and math.isclose(contract["target_value"], summary.target_value, rel_tol=1e-9, abs_tol=1e-9)
        and contract["operator"] == summary.operator
        and math.isclose(contract["tolerance"], summary.tolerance, rel_tol=1e-9, abs_tol=1e-9)
        and math.isclose(contract["observed_value"], summary.observed_value, rel_tol=1e-9, abs_tol=1e-9)
        and math.isclose(contract["target_gap"], summary.target_gap, rel_tol=1e-9, abs_tol=1e-9)
        and contract["target_met"] is summary.target_met
    )


def explicit_target_claim(claim: str | None) -> str | None:
    text = (claim or "").strip()
    if not text:
        return None
    met = any(pattern.search(text) for pattern in _MET_PATTERNS)
    missed = any(pattern.search(text) for pattern in _MISSED_PATTERNS)
    if met and missed:
        return "ambiguous"
    if met:
        return "met"
    if missed:
        return "missed"
    return None


def spec_has_target_rule(spec: Mapping[str, Any], target_value: float) -> bool:
    """Return whether one visible rule encodes the declared scalar target."""

    def walk(node: Any) -> bool:
        if isinstance(node, Mapping):
            mark = node.get("mark")
            mark_type = mark.get("type") if isinstance(mark, Mapping) else mark
            encoding = node.get("encoding")
            if mark_type == "rule" and isinstance(encoding, Mapping):
                for channel in ("y", "x"):
                    definition = encoding.get(channel)
                    if isinstance(definition, Mapping) and "datum" in definition:
                        datum = definition.get("datum")
                        if isinstance(datum, bool):
                            continue
                        if isinstance(datum, (int, float)) and math.isfinite(float(datum)):
                            if math.isclose(float(datum), target_value, rel_tol=1e-9, abs_tol=1e-9):
                                return True
            return any(walk(value) for value in node.values())
        if isinstance(node, list):
            return any(walk(value) for value in node)
        return False

    return walk(spec)


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"usermeta.target_contract.{field} must be a non-empty string.")
    return value.strip()


def _selector_value(value: Any, field: str) -> str | int | float:
    if isinstance(value, bool) or value is None:
        raise ValueError(
            f"usermeta.target_contract.{field} must be a non-empty string or finite number."
        )
    if isinstance(value, str):
        if not value.strip():
            raise ValueError(
                f"usermeta.target_contract.{field} must be a non-empty string or finite number."
            )
        return value
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(
                f"usermeta.target_contract.{field} must be a non-empty string or finite number."
            )
        return value
    raise ValueError(
        f"usermeta.target_contract.{field} must be a non-empty string or finite number."
    )


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"usermeta.target_contract.{field} must be a finite number.")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"usermeta.target_contract.{field} must be a finite number.")
    return number


def _nonnegative_number(value: Any, field: str) -> float:
    number = _finite_number(value, field)
    if number < 0:
        raise ValueError(f"usermeta.target_contract.{field} must be non-negative.")
    return number


def _operator(value: Any) -> str:
    if value not in TARGET_OPERATORS:
        raise ValueError(
            "usermeta.target_contract.operator must be 'at_least', 'at_most', or 'equal'."
        )
    return value
