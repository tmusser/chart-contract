"""Explicit measurement-unit identity and fixed-scale conversion contracts."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import pandas as pd

UNIT_CONVERSION_CONTRACT_KEY = "unit_conversion_contract"
UNIT_CONVERSION_CONTRACT_VERSION = 1
UNIT_CONVERSION_INTENTS = {"trend", "rank", "compare"}
CONVERSION_KINDS = {"identity", "scale"}


def chart_unit_conversion_contract(chart: Any) -> dict[str, Any] | None:
    """Return first-party unit metadata when any conversion semantics are declared."""

    values = (
        getattr(chart, "source_unit", None),
        getattr(chart, "conversion_kind", None),
        getattr(chart, "conversion_factor", None),
        getattr(chart, "conversion_basis", None),
        getattr(chart, "source_value_field", None),
        getattr(chart, "source_unit_basis_field", None),
    )
    if all(value is None for value in values):
        return None

    return {
        "version": UNIT_CONVERSION_CONTRACT_VERSION,
        "metric_field": getattr(chart, "y", None),
        "source_unit": getattr(chart, "source_unit", None),
        "display_unit": getattr(chart, "unit", None),
        "conversion_kind": getattr(chart, "conversion_kind", None),
        "conversion_factor": getattr(chart, "conversion_factor", None),
        "conversion_basis": getattr(chart, "conversion_basis", None),
        "source_value_field": getattr(chart, "source_value_field", None),
        "source_unit_basis_field": getattr(chart, "source_unit_basis_field", None),
    }


def parse_unit_conversion_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or UNIT_CONVERSION_CONTRACT_KEY not in usermeta:
        return None

    contract = usermeta.get(UNIT_CONVERSION_CONTRACT_KEY)
    if not isinstance(contract, Mapping):
        raise ValueError("usermeta.unit_conversion_contract must be an object.")

    expected_fields = {
        "version",
        "metric_field",
        "source_unit",
        "display_unit",
        "conversion_kind",
        "conversion_factor",
        "conversion_basis",
        "source_value_field",
        "source_unit_basis_field",
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
            "usermeta.unit_conversion_contract must use the exact v1 field set"
            + (" (" + "; ".join(details) + ")" if details else "")
            + "."
        )

    if contract.get("version") != UNIT_CONVERSION_CONTRACT_VERSION:
        raise ValueError(
            "usermeta.unit_conversion_contract.version must equal "
            f"{UNIT_CONVERSION_CONTRACT_VERSION}."
        )

    metric_field = _required_string(contract.get("metric_field"), "metric_field")
    source_unit = _required_string(contract.get("source_unit"), "source_unit")
    display_unit = _required_string(contract.get("display_unit"), "display_unit")
    conversion_kind = contract.get("conversion_kind")
    if conversion_kind not in CONVERSION_KINDS:
        raise ValueError(
            "usermeta.unit_conversion_contract.conversion_kind must be "
            "'identity' or 'scale'."
        )

    source_unit_basis_field = _optional_string(
        contract.get("source_unit_basis_field"),
        "source_unit_basis_field",
    )

    if conversion_kind == "identity":
        if source_unit != display_unit:
            raise ValueError("identity conversion requires source_unit == display_unit.")
        factor = _finite_number(contract.get("conversion_factor"), "conversion_factor")
        if not math.isclose(factor, 1.0, rel_tol=0.0, abs_tol=0.0):
            raise ValueError("identity conversion requires conversion_factor == 1.0.")
        if contract.get("conversion_basis") is not None:
            raise ValueError("identity conversion requires conversion_basis=null.")
        if contract.get("source_value_field") is not None:
            raise ValueError("identity conversion requires source_value_field=null.")
        conversion_basis = None
        source_value_field = None
    else:
        if source_unit == display_unit:
            raise ValueError("scale conversion requires different source and display units.")
        factor = _finite_number(contract.get("conversion_factor"), "conversion_factor")
        if factor <= 0:
            raise ValueError("scale conversion requires conversion_factor > 0.")
        conversion_basis = _required_string(
            contract.get("conversion_basis"),
            "conversion_basis",
        )
        source_value_field = _required_string(
            contract.get("source_value_field"),
            "source_value_field",
        )
        if source_value_field == metric_field:
            raise ValueError(
                "scale conversion source_value_field must differ from metric_field."
            )

    return {
        "version": UNIT_CONVERSION_CONTRACT_VERSION,
        "metric_field": metric_field,
        "source_unit": source_unit,
        "display_unit": display_unit,
        "conversion_kind": conversion_kind,
        "conversion_factor": factor,
        "conversion_basis": conversion_basis,
        "source_value_field": source_value_field,
        "source_unit_basis_field": source_unit_basis_field,
    }


def source_unit_basis_status(
    frame: pd.DataFrame,
    *,
    basis_field: str,
    source_unit: str,
) -> tuple[bool, str]:
    """Verify row-level source-unit identity."""

    if basis_field not in frame.columns:
        return False, f"Declared source-unit basis field '{basis_field}' is missing from the data."

    series = frame[basis_field]
    if series.isna().any():
        return False, f"Source-unit basis field '{basis_field}' contains null values."

    values: list[str] = []
    for raw in series.tolist():
        if not isinstance(raw, str) or not raw.strip():
            return False, (
                f"Source-unit basis field '{basis_field}' must contain non-empty string identities."
            )
        values.append(raw.strip())

    unique = sorted(set(values))
    if len(unique) != 1:
        return False, (
            f"Source-unit basis field '{basis_field}' contains mixed source units: "
            + ", ".join(repr(value) for value in unique)
            + "."
        )

    if unique[0] != source_unit:
        return False, (
            f"Source-unit basis field '{basis_field}' declares {unique[0]!r}, "
            f"but the unit conversion contract declares {source_unit!r}."
        )

    return True, (
        f"Source-unit basis field '{basis_field}' is complete and consistently declares "
        f"{source_unit!r}."
    )


def conversion_arithmetic_status(
    frame: pd.DataFrame,
    *,
    metric_field: str,
    source_value_field: str,
    conversion_factor: float,
) -> tuple[bool, str]:
    """Recompute one fixed multiplicative source->display conversion."""

    missing = [
        field
        for field in (metric_field, source_value_field)
        if field not in frame.columns
    ]
    if missing:
        return False, "Unit conversion evidence is missing field(s): " + ", ".join(missing) + "."

    checked = 0
    mismatches = 0
    for source_raw, metric_raw in zip(
        frame[source_value_field].tolist(),
        frame[metric_field].tolist(),
    ):
        source_missing = pd.isna(source_raw)
        metric_missing = pd.isna(metric_raw)
        if source_missing and metric_missing:
            continue
        if source_missing != metric_missing:
            return False, (
                "Unit conversion source/display values must be jointly present or jointly null."
            )
        if isinstance(source_raw, bool) or isinstance(metric_raw, bool):
            return False, "Unit conversion source/display values must be numeric, not boolean."
        try:
            source_value = float(source_raw)
            metric_value = float(metric_raw)
        except (TypeError, ValueError):
            return False, "Unit conversion source/display values must be numeric."
        if not math.isfinite(source_value) or not math.isfinite(metric_value):
            return False, "Unit conversion source/display values must be finite."
        checked += 1
        expected = source_value * conversion_factor
        if not math.isclose(metric_value, expected, rel_tol=1e-9, abs_tol=1e-9):
            mismatches += 1

    if checked == 0:
        return False, "Unit conversion has no complete numeric source/display observations."
    if mismatches:
        return False, (
            f"Fixed conversion arithmetic disagrees for {mismatches} of {checked} "
            "complete observation(s)."
        )

    return True, (
        f"Fixed conversion arithmetic reproduces {checked} complete observation(s) "
        f"with factor {conversion_factor:g}."
    )


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"usermeta.unit_conversion_contract.{field} must be a non-empty string."
        )
    return value.strip()


def _optional_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"usermeta.unit_conversion_contract.{field} must be null or a non-empty string."
        )
    return value.strip()


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"usermeta.unit_conversion_contract.{field} must be a finite number."
        )
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(
            f"usermeta.unit_conversion_contract.{field} must be a finite number."
        )
    return number
