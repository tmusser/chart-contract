"""Explicit metric directionality and evaluative comparison semantics."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

DIRECTIONALITY_CONTRACT_KEY = "directionality_contract"
DIRECTIONALITY_CONTRACT_VERSION = 1
DIRECTIONALITY_INTENTS = {"trend", "compare"}
DIRECTIONS = {"higher_is_better", "lower_is_better", "neutral"}

_IMPROVEMENT_PATTERNS = (
    re.compile(r"\bimprov(?:e|ed|ement|ements|ing)\b", re.IGNORECASE),
    re.compile(r"\bbetter\b", re.IGNORECASE),
)
_WORSENING_PATTERNS = (
    re.compile(r"\bwors(?:e|ened|ening)\b", re.IGNORECASE),
    re.compile(r"\bdeteriorat(?:e|ed|ion|ions|ing)\b", re.IGNORECASE),
)


def chart_directionality_contract(chart: Any) -> dict[str, Any] | None:
    direction = getattr(chart, "metric_direction", None)
    if direction is None:
        return None
    return {
        "version": DIRECTIONALITY_CONTRACT_VERSION,
        "metric_field": getattr(chart, "y", None),
        "direction": direction,
    }


def parse_directionality_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or DIRECTIONALITY_CONTRACT_KEY not in usermeta:
        return None

    contract = usermeta.get(DIRECTIONALITY_CONTRACT_KEY)
    if not isinstance(contract, Mapping):
        raise ValueError("usermeta.directionality_contract must be an object.")

    expected_fields = {"version", "metric_field", "direction"}
    if set(contract) != expected_fields:
        missing = sorted(expected_fields - set(contract))
        extra = sorted(set(contract) - expected_fields)
        details: list[str] = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("unsupported: " + ", ".join(extra))
        raise ValueError(
            "usermeta.directionality_contract must use the exact v1 field set"
            + (" (" + "; ".join(details) + ")" if details else "")
            + "."
        )

    if contract.get("version") != DIRECTIONALITY_CONTRACT_VERSION:
        raise ValueError(
            "usermeta.directionality_contract.version must equal "
            f"{DIRECTIONALITY_CONTRACT_VERSION}."
        )

    metric_field = contract.get("metric_field")
    if not isinstance(metric_field, str) or not metric_field.strip():
        raise ValueError(
            "usermeta.directionality_contract.metric_field must be a non-empty string."
        )

    direction = contract.get("direction")
    if direction not in DIRECTIONS:
        raise ValueError(
            "usermeta.directionality_contract.direction must be "
            "'higher_is_better', 'lower_is_better', or 'neutral'."
        )

    return {
        "version": DIRECTIONALITY_CONTRACT_VERSION,
        "metric_field": metric_field.strip(),
        "direction": direction,
    }


def explicit_evaluative_claim(claim: str | None) -> str | None:
    """Recover only narrow better/worse semantics from claim text."""

    text = (claim or "").strip()
    if not text:
        return None

    improvement = any(pattern.search(text) for pattern in _IMPROVEMENT_PATTERNS)
    worsening = any(pattern.search(text) for pattern in _WORSENING_PATTERNS)
    if improvement and worsening:
        return "ambiguous"
    if improvement:
        return "improvement"
    if worsening:
        return "worsening"
    return None


def movement_semantics(
    baseline: float,
    target: float,
    *,
    direction: str,
) -> str:
    """Classify target movement under one declared directional utility."""

    if baseline == target:
        return "unchanged"
    if direction == "neutral":
        return "neutral"

    rose = target > baseline
    beneficial = rose if direction == "higher_is_better" else not rose
    return "improvement" if beneficial else "worsening"
