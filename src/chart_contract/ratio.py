"""Explicit numerator/denominator semantics for ratio-like metrics."""

from __future__ import annotations

from collections.abc import Mapping
import math
from numbers import Real
from typing import Any

import pandas as pd

RATIO_CONTRACT_KEY = "ratio_contract"
RATIO_CONTRACT_VERSION = 1
RATIO_ARITHMETIC_VERSION = 2
RATIO_INTENTS = {"trend", "rank", "compare"}


def chart_ratio_contract(chart: Any) -> dict[str, Any] | None:
    """Return first-party ratio metadata when any ratio semantics are declared."""

    values = (
        getattr(chart, "numerator", None),
        getattr(chart, "denominator", None),
        getattr(chart, "cohort", None),
        getattr(chart, "denominator_basis_field", None),
        getattr(chart, "numerator_value_field", None),
        getattr(chart, "denominator_value_field", None),
        getattr(chart, "ratio_multiplier", None),
        getattr(chart, "ratio_tolerance", None),
    )
    if all(value is None for value in values):
        return None

    metric_field = getattr(chart, "y", None)
    arithmetic_requested = any(
        getattr(chart, name, None) is not None
        for name in ("numerator_value_field", "denominator_value_field",
                     "ratio_multiplier", "ratio_tolerance")
    )
    result = {
        "version": RATIO_ARITHMETIC_VERSION if arithmetic_requested else RATIO_CONTRACT_VERSION,
        "metric_field": metric_field,
        "numerator": getattr(chart, "numerator", None),
        "denominator": getattr(chart, "denominator", None),
        "cohort": getattr(chart, "cohort", None),
        "denominator_basis_field": getattr(chart, "denominator_basis_field", None),
    }
    if arithmetic_requested:
        result.update(
            numerator_value_field=getattr(chart, "numerator_value_field", None),
            denominator_value_field=getattr(chart, "denominator_value_field", None),
            ratio_multiplier=(
                1.0 if getattr(chart, "ratio_multiplier", None) is None
                else getattr(chart, "ratio_multiplier")
            ),
            ratio_tolerance=(
                1e-9 if getattr(chart, "ratio_tolerance", None) is None
                else getattr(chart, "ratio_tolerance")
            ),
        )
    return result


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
    version = contract.get("version")
    if type(version) is not int or version not in (RATIO_CONTRACT_VERSION, RATIO_ARITHMETIC_VERSION):
        raise ValueError("usermeta.ratio_contract.version must equal 1 or 2.")
    if version == RATIO_ARITHMETIC_VERSION:
        expected_fields |= {
            "numerator_value_field", "denominator_value_field",
            "ratio_multiplier", "ratio_tolerance",
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
            f"usermeta.ratio_contract must use the exact v{version} field set"
            + (" (" + "; ".join(details) + ")" if details else "")
            + "."
        )

    metric_field = _required_string(contract.get("metric_field"), "metric_field")
    numerator = _required_string(contract.get("numerator"), "numerator")
    denominator = _required_string(contract.get("denominator"), "denominator")
    cohort = _optional_string(contract.get("cohort"), "cohort")
    denominator_basis_field = _optional_string(
        contract.get("denominator_basis_field"),
        "denominator_basis_field",
    )

    result = {
        "version": version,
        "metric_field": metric_field,
        "numerator": numerator,
        "denominator": denominator,
        "cohort": cohort,
        "denominator_basis_field": denominator_basis_field,
    }
    if version == RATIO_ARITHMETIC_VERSION:
        numerator_field = _required_string(contract.get("numerator_value_field"), "numerator_value_field")
        denominator_field = _required_string(contract.get("denominator_value_field"), "denominator_value_field")
        if len({metric_field, numerator_field, denominator_field}) != 3:
            raise ValueError("Ratio metric, numerator, and denominator value fields must be distinct.")
        result.update(
            numerator_value_field=numerator_field,
            denominator_value_field=denominator_field,
            ratio_multiplier=_finite_number(contract.get("ratio_multiplier"), "ratio_multiplier", positive=True),
            ratio_tolerance=_finite_number(contract.get("ratio_tolerance"), "ratio_tolerance"),
        )
    return result


def _finite_number(value: Any, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"usermeta.ratio_contract.{field} must be a finite number.")
    if (value <= 0 if positive else value < 0):
        raise ValueError(f"usermeta.ratio_contract.{field} must be {'positive' if positive else 'non-negative'}.")
    return float(value)


def ratio_arithmetic_status(frame: pd.DataFrame, contract: Mapping[str, Any]) -> tuple[bool, str]:
    """Recompute every declared row without modifying the supplied metric."""

    fields = (
        contract["metric_field"], contract["numerator_value_field"],
        contract["denominator_value_field"],
    )
    absent = [name for name in fields if name not in frame.columns]
    if absent:
        return False, "Ratio arithmetic evidence field(s) missing: " + ", ".join(absent) + "."
    if frame.empty:
        return False, "Ratio arithmetic requires at least one supplied observation."
    largest_error = 0.0
    for position, (reported, numerator, denominator) in enumerate(
        frame[list(fields)].itertuples(index=False, name=None), start=1
    ):
        for name, value in zip(fields, (reported, numerator, denominator)):
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
                return False, f"Ratio arithmetic row {position} has a non-finite or non-numeric {name!r} value."
        if denominator <= 0:
            return False, f"Ratio arithmetic row {position} has a zero or negative denominator."
        expected = numerator / denominator * contract["ratio_multiplier"]
        if not math.isfinite(expected):
            return False, f"Ratio arithmetic row {position} has a non-finite computed ratio."
        difference = abs(reported - expected)
        if not math.isfinite(difference):
            return False, f"Ratio arithmetic row {position} has a non-finite arithmetic difference."
        largest_error = max(largest_error, difference)
        if not math.isclose(reported, expected, rel_tol=0.0, abs_tol=contract["ratio_tolerance"]):
            return False, (
                f"Ratio arithmetic mismatch at row {position}: observed {reported:g}, "
                f"computed {expected:g} from {numerator:g}/{denominator:g} "
                f"× {contract['ratio_multiplier']:g}; "
                f"absolute error {difference:g} exceeds tolerance {contract['ratio_tolerance']:g}."
            )
    return True, (
        f"Ratio arithmetic reproduces {len(frame)} displayed value(s) from source numerator/denominator; "
        f"maximum absolute error {largest_error:g} (tolerance {contract['ratio_tolerance']:g})."
    )


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
