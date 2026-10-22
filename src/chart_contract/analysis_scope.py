"""Explicit analysis-scope identity for descriptive analytical evidence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

ANALYSIS_SCOPE_CONTRACT_KEY = "analysis_scope_contract"
ANALYSIS_SCOPE_CONTRACT_VERSION = 1
ANALYSIS_SCOPE_INTENTS = {"trend", "rank", "compare"}


def chart_analysis_scope_contract(chart: Any) -> dict[str, Any] | None:
    """Return first-party scope metadata when any scope identity is declared."""

    values = (
        getattr(chart, "scope_id", None),
        getattr(chart, "scope_definition", None),
        getattr(chart, "scope_version", None),
        getattr(chart, "scope_basis_field", None),
        getattr(chart, "scope_basis_value", None),
    )
    if all(value is None for value in values):
        return None

    return {
        "version": ANALYSIS_SCOPE_CONTRACT_VERSION,
        "scope_id": getattr(chart, "scope_id", None),
        "scope_definition": getattr(chart, "scope_definition", None),
        "scope_version": getattr(chart, "scope_version", None),
        "scope_basis_field": getattr(chart, "scope_basis_field", None),
        "scope_basis_value": getattr(chart, "scope_basis_value", None),
    }


def parse_analysis_scope_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or ANALYSIS_SCOPE_CONTRACT_KEY not in usermeta:
        return None

    contract = usermeta.get(ANALYSIS_SCOPE_CONTRACT_KEY)
    if not isinstance(contract, Mapping):
        raise ValueError("usermeta.analysis_scope_contract must be an object.")

    expected_fields = {
        "version",
        "scope_id",
        "scope_definition",
        "scope_version",
        "scope_basis_field",
        "scope_basis_value",
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
            "usermeta.analysis_scope_contract must use the exact v1 field set"
            + (" (" + "; ".join(details) + ")" if details else "")
            + "."
        )

    if contract.get("version") != ANALYSIS_SCOPE_CONTRACT_VERSION:
        raise ValueError(
            "usermeta.analysis_scope_contract.version must equal "
            f"{ANALYSIS_SCOPE_CONTRACT_VERSION}."
        )

    scope_id = _required_string(contract.get("scope_id"), "scope_id")
    scope_definition = _required_string(
        contract.get("scope_definition"),
        "scope_definition",
    )
    scope_version = _required_string(
        contract.get("scope_version"),
        "scope_version",
    )
    scope_basis_field = _optional_string(
        contract.get("scope_basis_field"),
        "scope_basis_field",
    )
    scope_basis_value = _optional_string(
        contract.get("scope_basis_value"),
        "scope_basis_value",
    )

    if (scope_basis_field is None) != (scope_basis_value is None):
        raise ValueError(
            "usermeta.analysis_scope_contract.scope_basis_field and "
            "scope_basis_value must be declared together or both null."
        )

    return {
        "version": ANALYSIS_SCOPE_CONTRACT_VERSION,
        "scope_id": scope_id,
        "scope_definition": scope_definition,
        "scope_version": scope_version,
        "scope_basis_field": scope_basis_field,
        "scope_basis_value": scope_basis_value,
    }


def scope_basis_status(
    frame: pd.DataFrame,
    *,
    basis_field: str,
    basis_value: str,
) -> tuple[bool, str]:
    """Verify supplied rows consistently carry the declared scope identity."""

    if basis_field not in frame.columns:
        return False, f"Declared scope basis field '{basis_field}' is missing from the data."

    series = frame[basis_field]
    if series.isna().any():
        return False, f"Scope basis field '{basis_field}' contains null values."

    values: list[str] = []
    for raw in series.tolist():
        if not isinstance(raw, str) or not raw.strip():
            return False, (
                f"Scope basis field '{basis_field}' must contain non-empty string identities."
            )
        values.append(raw.strip())

    unique = sorted(set(values))
    if len(unique) != 1:
        return False, (
            f"Scope basis field '{basis_field}' contains mixed analysis scopes: "
            + ", ".join(repr(value) for value in unique)
            + "."
        )

    if unique[0] != basis_value:
        return False, (
            f"Scope basis field '{basis_field}' declares {unique[0]!r}, "
            f"but the analysis scope contract expects {basis_value!r}."
        )

    return True, (
        f"Scope basis field '{basis_field}' is complete and consistently declares "
        f"{basis_value!r}."
    )


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"usermeta.analysis_scope_contract.{field} must be a non-empty string."
        )
    return value.strip()


def _optional_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"usermeta.analysis_scope_contract.{field} must be null or a non-empty string."
        )
    return value.strip()
