"""Explicit semantic identity for quantitative metrics."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

METRIC_DEFINITION_CONTRACT_KEY = "metric_definition_contract"
METRIC_DEFINITION_CONTRACT_VERSION = 1
METRIC_DEFINITION_INTENTS = {"trend", "rank", "compare"}


def chart_metric_definition_contract(chart: Any) -> dict[str, Any] | None:
    """Return first-party metric-definition metadata when any identity is declared."""

    values = (
        getattr(chart, "metric_id", None),
        getattr(chart, "metric_definition", None),
        getattr(chart, "metric_version", None),
        getattr(chart, "metric_basis_field", None),
    )
    if all(value is None for value in values):
        return None

    return {
        "version": METRIC_DEFINITION_CONTRACT_VERSION,
        "metric_field": getattr(chart, "y", None),
        "metric_id": getattr(chart, "metric_id", None),
        "metric_definition": getattr(chart, "metric_definition", None),
        "metric_version": getattr(chart, "metric_version", None),
        "metric_basis_field": getattr(chart, "metric_basis_field", None),
    }


def parse_metric_definition_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or METRIC_DEFINITION_CONTRACT_KEY not in usermeta:
        return None

    contract = usermeta.get(METRIC_DEFINITION_CONTRACT_KEY)
    if not isinstance(contract, Mapping):
        raise ValueError("usermeta.metric_definition_contract must be an object.")

    expected_fields = {
        "version",
        "metric_field",
        "metric_id",
        "metric_definition",
        "metric_version",
        "metric_basis_field",
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
            "usermeta.metric_definition_contract must use the exact v1 field set"
            + (" (" + "; ".join(details) + ")" if details else "")
            + "."
        )

    if contract.get("version") != METRIC_DEFINITION_CONTRACT_VERSION:
        raise ValueError(
            "usermeta.metric_definition_contract.version must equal "
            f"{METRIC_DEFINITION_CONTRACT_VERSION}."
        )

    return {
        "version": METRIC_DEFINITION_CONTRACT_VERSION,
        "metric_field": _required_string(contract.get("metric_field"), "metric_field"),
        "metric_id": _required_string(contract.get("metric_id"), "metric_id"),
        "metric_definition": _required_string(
            contract.get("metric_definition"),
            "metric_definition",
        ),
        "metric_version": _required_string(contract.get("metric_version"), "metric_version"),
        "metric_basis_field": _optional_string(
            contract.get("metric_basis_field"),
            "metric_basis_field",
        ),
    }


def metric_basis_status(
    frame: pd.DataFrame,
    *,
    basis_field: str,
    metric_version: str,
) -> tuple[bool, str]:
    """Verify that supplied rows consistently declare the contracted metric version."""

    if basis_field not in frame.columns:
        return False, f"Declared metric basis field '{basis_field}' is missing from the data."

    series = frame[basis_field]
    if series.isna().any():
        return False, f"Metric basis field '{basis_field}' contains null values."

    values: list[str] = []
    for raw in series.tolist():
        if not isinstance(raw, str) or not raw.strip():
            return False, (
                f"Metric basis field '{basis_field}' must contain non-empty string versions."
            )
        values.append(raw.strip())

    unique = sorted(set(values))
    if len(unique) != 1:
        return False, (
            f"Metric basis field '{basis_field}' contains mixed metric versions: "
            + ", ".join(repr(value) for value in unique)
            + "."
        )

    if unique and unique[0] != metric_version:
        return False, (
            f"Metric basis field '{basis_field}' declares version {unique[0]!r}, "
            f"but the metric definition contract declares {metric_version!r}."
        )

    return True, (
        f"Metric basis field '{basis_field}' is complete and consistently declares "
        f"version {metric_version!r}."
    )


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"usermeta.metric_definition_contract.{field} must be a non-empty string."
        )
    return value.strip()


def _optional_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"usermeta.metric_definition_contract.{field} must be null or a non-empty string."
        )
    return value.strip()
