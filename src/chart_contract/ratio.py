"""Explicit numerator/denominator semantics for ratio-like metrics."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

RATIO_CONTRACT_KEY = "ratio_contract"
RATIO_CONTRACT_VERSION = 1
RATIO_INTENTS = {"trend", "rank", "compare"}


def chart_ratio_contract(chart: Any) -> dict[str, Any] | None:
    """Return first-party ratio metadata when any ratio semantics are declared."""

    values = (
        getattr(chart, "numerator", None),
        getattr(chart, "denominator", None),
        getattr(chart, "cohort", None),
        getattr(chart, "denominator_basis_field", None),
    )
    if all(value is None for value in values):
        return None

    metric_field = getattr(chart, "y", None)
    return {
        "version": RATIO_CONTRACT_VERSION,
        "metric_field": metric_field,
        "numerator": getattr(chart, "numerator", None),
        "denominator": getattr(chart, "denominator", None),
        "cohort": getattr(chart, "cohort", None),
        "denominator_basis_field": getattr(chart, "denominator_basis_field", None),
    }


def parse_ratio_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or RATIO_CONTRACT_KEY not in usermeta:
        return None

    contract = usermeta.get(RATIO_CONTRACT_KEY)
    if not isinstance(contract, Mapping):
        raise ValueError("usermeta.ratio_contract must be an object.")

    expected_fields = {
        "version",
        "metric_field",
        "numerator",
        "denominator",
        "cohort",
        "denominator_basis_field",
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
            "usermeta.ratio_contract must use the exact v1 field set"
            + (" (" + "; ".join(details) + ")" if details else "")
            + "."
        )

    if contract.get("version") != RATIO_CONTRACT_VERSION:
        raise ValueError(f"usermeta.ratio_contract.version must equal {RATIO_CONTRACT_VERSION}.")

    metric_field = _required_string(contract.get("metric_field"), "metric_field")
    numerator = _required_string(contract.get("numerator"), "numerator")
    denominator = _required_string(contract.get("denominator"), "denominator")
    cohort = _optional_string(contract.get("cohort"), "cohort")
    denominator_basis_field = _optional_string(
        contract.get("denominator_basis_field"),
        "denominator_basis_field",
    )

    return {
        "version": RATIO_CONTRACT_VERSION,
        "metric_field": metric_field,
        "numerator": numerator,
        "denominator": denominator,
        "cohort": cohort,
        "denominator_basis_field": denominator_basis_field,
    }


def denominator_basis_status(
    frame: pd.DataFrame,
    *,
    basis_field: str,
    denominator: str,
) -> tuple[bool, str]:
    """Verify that a declared row-level denominator basis is complete and invariant."""

    if basis_field not in frame.columns:
        return False, f"Declared denominator basis field '{basis_field}' is missing from the data."

    series = frame[basis_field]
    if series.isna().any():
        return False, f"Denominator basis field '{basis_field}' contains null values."

    values: list[str] = []
    for raw in series.tolist():
        if not isinstance(raw, str) or not raw.strip():
            return False, (
                f"Denominator basis field '{basis_field}' must contain non-empty string identities."
            )
        values.append(raw.strip())

    unique = sorted(set(values))
    if len(unique) != 1:
        return False, (
            f"Denominator basis field '{basis_field}' contains mixed denominator identities: "
            + ", ".join(repr(value) for value in unique)
            + "."
        )

    if unique and unique[0] != denominator:
        return False, (
            f"Denominator basis field '{basis_field}' declares {unique[0]!r}, "
            f"but the ratio contract declares {denominator!r}."
        )

    return True, (
        f"Denominator basis field '{basis_field}' is complete and consistently declares "
        f"{denominator!r}."
    )


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"usermeta.ratio_contract.{field} must be a non-empty string.")
    return value.strip()


def _optional_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"usermeta.ratio_contract.{field} must be null or a non-empty string."
        )
    return value.strip()
