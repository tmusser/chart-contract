"""Explicit uncertainty interval semantics for analytical estimates."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Any

import pandas as pd

UNCERTAINTY_CONTRACT_KEY = "uncertainty_contract"
UNCERTAINTY_CONTRACT_VERSION = 1
UNCERTAINTY_INTENTS = {"trend", "compare"}
INTERVAL_KINDS = {"confidence", "credible", "prediction", "bootstrap"}

_EXPLICIT_INTERVAL_PATTERNS = (
    (re.compile(r"\b(\d+(?:\.\d+)?)\s*%\s*(?:confidence\s+interval|ci)\b", re.IGNORECASE), "confidence"),
    (re.compile(r"\b(\d+(?:\.\d+)?)\s*%\s*credible\s+interval\b", re.IGNORECASE), "credible"),
    (re.compile(r"\b(\d+(?:\.\d+)?)\s*%\s*prediction\s+interval\b", re.IGNORECASE), "prediction"),
    (re.compile(r"\b(\d+(?:\.\d+)?)\s*%\s*bootstrap\s+interval\b", re.IGNORECASE), "bootstrap"),
)


def chart_uncertainty_contract(chart: Any) -> dict[str, Any] | None:
    """Return first-party interval metadata when any uncertainty semantics are declared."""

    values = (
        getattr(chart, "interval_lower_field", None),
        getattr(chart, "interval_upper_field", None),
        getattr(chart, "interval_kind", None),
        getattr(chart, "interval_level", None),
        getattr(chart, "interval_method", None),
    )
    if all(value is None for value in values):
        return None

    return {
        "version": UNCERTAINTY_CONTRACT_VERSION,
        "estimate_field": getattr(chart, "y", None),
        "lower_field": getattr(chart, "interval_lower_field", None),
        "upper_field": getattr(chart, "interval_upper_field", None),
        "interval_kind": getattr(chart, "interval_kind", None),
        "interval_level": getattr(chart, "interval_level", None),
        "interval_method": getattr(chart, "interval_method", None),
    }


def parse_uncertainty_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or UNCERTAINTY_CONTRACT_KEY not in usermeta:
        return None

    contract = usermeta.get(UNCERTAINTY_CONTRACT_KEY)
    if not isinstance(contract, Mapping):
        raise ValueError("usermeta.uncertainty_contract must be an object.")

    expected_fields = {
        "version",
        "estimate_field",
        "lower_field",
        "upper_field",
        "interval_kind",
        "interval_level",
        "interval_method",
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
            "usermeta.uncertainty_contract must use the exact v1 field set"
            + (" (" + "; ".join(details) + ")" if details else "")
            + "."
        )

    if contract.get("version") != UNCERTAINTY_CONTRACT_VERSION:
        raise ValueError(
            "usermeta.uncertainty_contract.version must equal "
            f"{UNCERTAINTY_CONTRACT_VERSION}."
        )

    estimate_field = _required_string(contract.get("estimate_field"), "estimate_field")
    lower_field = _required_string(contract.get("lower_field"), "lower_field")
    upper_field = _required_string(contract.get("upper_field"), "upper_field")
    if len({estimate_field, lower_field, upper_field}) != 3:
        raise ValueError(
            "usermeta.uncertainty_contract estimate/lower/upper fields must be distinct."
        )

    interval_kind = contract.get("interval_kind")
    if interval_kind not in INTERVAL_KINDS:
        raise ValueError(
            "usermeta.uncertainty_contract.interval_kind must be one of: "
            + ", ".join(sorted(INTERVAL_KINDS))
            + "."
        )

    level = contract.get("interval_level")
    if isinstance(level, bool) or not isinstance(level, (int, float)):
        raise ValueError(
            "usermeta.uncertainty_contract.interval_level must be a finite number in (0, 1)."
        )
    level = float(level)
    if not math.isfinite(level) or not 0.0 < level < 1.0:
        raise ValueError(
            "usermeta.uncertainty_contract.interval_level must be a finite number in (0, 1)."
        )

    method = _required_string(contract.get("interval_method"), "interval_method")

    return {
        "version": UNCERTAINTY_CONTRACT_VERSION,
        "estimate_field": estimate_field,
        "lower_field": lower_field,
        "upper_field": upper_field,
        "interval_kind": interval_kind,
        "interval_level": level,
        "interval_method": method,
    }


def interval_bounds_status(
    frame: pd.DataFrame,
    *,
    estimate_field: str,
    lower_field: str,
    upper_field: str,
) -> tuple[bool, str]:
    """Verify complete finite interval bounds contain every estimate."""

    missing = [
        field
        for field in (estimate_field, lower_field, upper_field)
        if field not in frame.columns
    ]
    if missing:
        return False, "Uncertainty evidence is missing field(s): " + ", ".join(missing) + "."

    checked = 0
    invalid_order = 0
    for estimate_raw, lower_raw, upper_raw in zip(
        frame[estimate_field].tolist(),
        frame[lower_field].tolist(),
        frame[upper_field].tolist(),
    ):
        values = (estimate_raw, lower_raw, upper_raw)
        if any(pd.isna(value) for value in values):
            return False, (
                "Uncertainty estimate/lower/upper fields must be jointly complete for every row."
            )
        if any(isinstance(value, bool) for value in values):
            return False, "Uncertainty estimate/lower/upper values must be numeric, not boolean."
        try:
            estimate, lower, upper = (float(value) for value in values)
        except (TypeError, ValueError):
            return False, "Uncertainty estimate/lower/upper values must be numeric."
        if not all(math.isfinite(value) for value in (estimate, lower, upper)):
            return False, "Uncertainty estimate/lower/upper values must be finite."
        checked += 1
        if lower > estimate or estimate > upper:
            invalid_order += 1

    if checked == 0:
        return False, "Uncertainty contract has no complete interval observations."
    if invalid_order:
        return False, (
            f"{invalid_order} of {checked} interval observation(s) do not satisfy "
            "lower <= estimate <= upper."
        )

    return True, (
        f"All {checked} interval observation(s) are finite and satisfy "
        "lower <= estimate <= upper."
    )


def parse_explicit_interval_claim(claim: str | None) -> tuple[str, float] | None:
    """Parse only explicit '<level>% <kind> interval' / '<level>% CI' wording."""

    if not isinstance(claim, str) or not claim.strip():
        return None

    matches: list[tuple[str, float]] = []
    for pattern, kind in _EXPLICIT_INTERVAL_PATTERNS:
        for match in pattern.finditer(claim):
            percent = float(match.group(1))
            if 0.0 < percent < 100.0:
                matches.append((kind, percent / 100.0))

    if not matches:
        return None
    unique = set(matches)
    if len(unique) != 1:
        return ("ambiguous", math.nan)
    return matches[0]


def interval_claim_status(
    claim: str | None,
    contract: Mapping[str, Any] | None,
) -> tuple[str | None, str | None]:
    """Check narrow explicit claim wording against declared interval semantics."""

    explicit = parse_explicit_interval_claim(claim)
    if explicit is None:
        return None, None

    if contract is None:
        return (
            "WARN",
            "Claim explicitly names an uncertainty interval but no uncertainty contract is declared.",
        )

    kind, level = explicit
    if kind == "ambiguous":
        return (
            "FAIL",
            "Claim contains conflicting explicit uncertainty interval semantics.",
        )
    if kind != contract["interval_kind"]:
        return (
            "FAIL",
            (
                f"Claim names {kind!r} interval semantics but the contract declares "
                f"{contract['interval_kind']!r}."
            ),
        )
    if not math.isclose(level, contract["interval_level"], rel_tol=0.0, abs_tol=1e-12):
        return (
            "FAIL",
            (
                f"Claim names interval level {level:.3f}, but the contract declares "
                f"{contract['interval_level']:.3f}."
            ),
        )

    return (
        "PASS",
        (
            f"Explicit claim interval semantics match {contract['interval_level'] * 100:g}% "
            f"{contract['interval_kind']} interval metadata."
        ),
    )


def spec_has_interval_binding(
    spec: Mapping[str, Any],
    *,
    estimate_field: str,
    lower_field: str,
    upper_field: str,
) -> bool:
    """Return whether the estimate and declared interval bounds are visibly bound."""

    def field(definition: Any) -> str | None:
        if isinstance(definition, Mapping):
            value = definition.get("field")
            return value if isinstance(value, str) else None
        if isinstance(definition, str):
            return definition.split(":", 1)[0]
        return None

    def mark_type(node: Mapping[str, Any]) -> str | None:
        mark = node.get("mark")
        if isinstance(mark, str):
            return mark
        if isinstance(mark, Mapping):
            value = mark.get("type")
            return value if isinstance(value, str) else None
        return None

    def visit(node: Any) -> bool:
        if not isinstance(node, Mapping):
            return False
        encoding = node.get("encoding")
        if mark_type(node) == "rule" and isinstance(encoding, Mapping):
            vertical = (
                field(encoding.get("y")) == lower_field
                and field(encoding.get("y2")) == upper_field
            )
            horizontal = (
                field(encoding.get("x")) == lower_field
                and field(encoding.get("x2")) == upper_field
            )
            if vertical or horizontal:
                return True
        for key in ("layer", "hconcat", "vconcat", "concat"):
            nested = node.get(key)
            if isinstance(nested, list) and any(visit(child) for child in nested):
                return True
        spec_child = node.get("spec")
        return visit(spec_child) if isinstance(spec_child, Mapping) else False

    def estimate_visible(node: Any) -> bool:
        if not isinstance(node, Mapping):
            return False
        encoding = node.get("encoding")
        if isinstance(encoding, Mapping):
            for channel in ("x", "y"):
                if field(encoding.get(channel)) == estimate_field:
                    return True
        for key in ("layer", "hconcat", "vconcat", "concat"):
            nested = node.get(key)
            if isinstance(nested, list) and any(estimate_visible(child) for child in nested):
                return True
        spec_child = node.get("spec")
        return estimate_visible(spec_child) if isinstance(spec_child, Mapping) else False

    return estimate_visible(spec) and visit(spec)


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"usermeta.uncertainty_contract.{field} must be a non-empty string."
        )
    return value.strip()
