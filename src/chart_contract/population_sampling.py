"""Explicit population and sampling semantics for analytical evidence."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Any

import pandas as pd

POPULATION_CONTRACT_KEY = "population_contract"
POPULATION_CONTRACT_VERSION = 1
POPULATION_INTENTS = {"trend", "rank", "compare"}

EVIDENCE_SCOPES = {"sample", "census"}
SAMPLING_METHODS = {
    "census",
    "simple_random",
    "stratified",
    "systematic",
    "cluster",
    "convenience",
    "quota",
    "unknown",
    "other",
}
NONPROBABILITY_METHODS = {"convenience", "quota", "unknown", "other"}


_EXPLICIT_SAMPLING_PATTERNS = (
    re.compile(r"\bsample\s+of\b", re.IGNORECASE),
    re.compile(r"\bsampled\s+from\b", re.IGNORECASE),
    re.compile(r"\bsurvey\s+respondents?\b", re.IGNORECASE),
    re.compile(r"\bcensus\s+of\b", re.IGNORECASE),
)


def claim_implies_sampling_scope(claim: str | None) -> bool:
    """Detect only narrow, explicit claim wording that names sampling scope."""

    if not isinstance(claim, str) or not claim.strip():
        return False
    return any(pattern.search(claim) for pattern in _EXPLICIT_SAMPLING_PATTERNS)


def chart_population_contract(chart: Any) -> dict[str, Any] | None:
    """Return first-party population metadata when any sampling semantics are declared."""

    values = (
        getattr(chart, "evidence_scope", None),
        getattr(chart, "population", None),
        getattr(chart, "population_size", None),
        getattr(chart, "sample_size", None),
        getattr(chart, "sampling_method", None),
        getattr(chart, "sample_member_field", None),
        getattr(chart, "weight_field", None),
        getattr(chart, "generalizes_to_population", None),
    )
    if all(value is None for value in values):
        return None

    return {
        "version": POPULATION_CONTRACT_VERSION,
        "evidence_scope": getattr(chart, "evidence_scope", None),
        "population": getattr(chart, "population", None),
        "population_size": getattr(chart, "population_size", None),
        "sample_size": getattr(chart, "sample_size", None),
        "sampling_method": getattr(chart, "sampling_method", None),
        "sample_member_field": getattr(chart, "sample_member_field", None),
        "weight_field": getattr(chart, "weight_field", None),
        "generalizes_to_population": getattr(chart, "generalizes_to_population", None),
    }


def parse_population_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or POPULATION_CONTRACT_KEY not in usermeta:
        return None

    contract = usermeta.get(POPULATION_CONTRACT_KEY)
    if not isinstance(contract, Mapping):
        raise ValueError("usermeta.population_contract must be an object.")

    expected_fields = {
        "version",
        "evidence_scope",
        "population",
        "population_size",
        "sample_size",
        "sampling_method",
        "sample_member_field",
        "weight_field",
        "generalizes_to_population",
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
            "usermeta.population_contract must use the exact v1 field set"
            + (" (" + "; ".join(details) + ")" if details else "")
            + "."
        )

    if contract.get("version") != POPULATION_CONTRACT_VERSION:
        raise ValueError(
            "usermeta.population_contract.version must equal "
            f"{POPULATION_CONTRACT_VERSION}."
        )

    evidence_scope = contract.get("evidence_scope")
    if evidence_scope not in EVIDENCE_SCOPES:
        raise ValueError(
            "usermeta.population_contract.evidence_scope must be 'sample' or 'census'."
        )

    population = _required_string(contract.get("population"), "population")
    population_size = _optional_positive_int(
        contract.get("population_size"),
        "population_size",
    )
    sample_size = _positive_int(contract.get("sample_size"), "sample_size")

    sampling_method = contract.get("sampling_method")
    if sampling_method not in SAMPLING_METHODS:
        allowed = ", ".join(sorted(SAMPLING_METHODS))
        raise ValueError(
            "usermeta.population_contract.sampling_method must be one of: "
            + allowed
            + "."
        )

    sample_member_field = _optional_string(
        contract.get("sample_member_field"),
        "sample_member_field",
    )
    weight_field = _optional_string(contract.get("weight_field"), "weight_field")
    generalizes = contract.get("generalizes_to_population")
    if not isinstance(generalizes, bool):
        raise ValueError(
            "usermeta.population_contract.generalizes_to_population must be boolean."
        )

    if evidence_scope == "census":
        if sampling_method != "census":
            raise ValueError("census evidence requires sampling_method='census'.")
        if population_size is None:
            raise ValueError("census evidence requires population_size.")
        if sample_size != population_size:
            raise ValueError(
                "census evidence requires sample_size == population_size."
            )
        if weight_field is not None:
            raise ValueError("census evidence does not support weight_field in v1.")
    else:
        if sampling_method == "census":
            raise ValueError("sample evidence cannot use sampling_method='census'.")
        if population_size is not None and sample_size >= population_size:
            raise ValueError(
                "sample evidence requires sample_size < population_size when "
                "population_size is declared."
            )

    return {
        "version": POPULATION_CONTRACT_VERSION,
        "evidence_scope": evidence_scope,
        "population": population,
        "population_size": population_size,
        "sample_size": sample_size,
        "sampling_method": sampling_method,
        "sample_member_field": sample_member_field,
        "weight_field": weight_field,
        "generalizes_to_population": generalizes,
    }


def sample_member_status(
    frame: pd.DataFrame,
    *,
    member_field: str,
    sample_size: int,
) -> tuple[bool, str]:
    """Verify optional row-level sample-member identity/count evidence."""

    if member_field not in frame.columns:
        return False, f"Declared sample member field '{member_field}' is missing from the data."

    series = frame[member_field]
    if series.isna().any():
        return False, f"Sample member field '{member_field}' contains null values."

    for raw in series.tolist():
        if isinstance(raw, str) and not raw.strip():
            return False, f"Sample member field '{member_field}' contains blank identifiers."

    unique_count = int(series.nunique(dropna=False))
    row_count = int(len(series))
    if unique_count != row_count:
        return False, (
            f"Sample member field '{member_field}' contains duplicate identifiers: "
            f"{unique_count} unique across {row_count} supplied rows."
        )
    if unique_count != sample_size:
        return False, (
            f"Sample member field '{member_field}' reconstructs {unique_count} members, "
            f"but the population contract declares sample_size={sample_size}."
        )

    return True, (
        f"Sample member field '{member_field}' reconstructs exactly "
        f"{sample_size} unique sampled member(s)."
    )


def weight_status(
    frame: pd.DataFrame,
    *,
    weight_field: str,
) -> tuple[bool, str]:
    """Verify optional row-level sampling weights are positive finite numerics."""

    if weight_field not in frame.columns:
        return False, f"Declared weight field '{weight_field}' is missing from the data."

    checked = 0
    for raw in frame[weight_field].tolist():
        if pd.isna(raw):
            return False, f"Weight field '{weight_field}' contains null values."
        if isinstance(raw, bool):
            return False, f"Weight field '{weight_field}' must be numeric, not boolean."
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return False, f"Weight field '{weight_field}' must contain numeric values."
        if not math.isfinite(value):
            return False, f"Weight field '{weight_field}' must contain finite values."
        if value <= 0:
            return False, f"Weight field '{weight_field}' must contain strictly positive values."
        checked += 1

    if checked == 0:
        return False, f"Weight field '{weight_field}' has no supplied observations."

    return True, (
        f"Weight field '{weight_field}' contains {checked} positive finite weight value(s)."
    )


def generalization_status(contract: Mapping[str, Any]) -> tuple[str, str]:
    """Classify explicit population-generalization intent without claim-text inference."""

    if not contract["generalizes_to_population"]:
        return "PASS", "Artifact does not declare population-level generalization."

    if contract["evidence_scope"] == "census":
        return "PASS", "Census evidence explicitly declares population-level generalization."

    method = contract["sampling_method"]
    if method in NONPROBABILITY_METHODS:
        return (
            "WARN",
            (
                "Artifact declares population-level generalization from "
                f"{method!r} sampling, which requires human review."
            ),
        )

    return (
        "PASS",
        (
            "Population-level generalization is explicitly declared with "
            f"sampling_method={method!r}; sampling metadata alone does not prove representativeness."
        ),
    )


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"usermeta.population_contract.{field} must be a non-empty string."
        )
    return value.strip()


def _optional_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"usermeta.population_contract.{field} must be null or a non-empty string."
        )
    return value.strip()


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(
            f"usermeta.population_contract.{field} must be a positive integer."
        )
    return value


def _optional_positive_int(value: Any, field: str) -> int | None:
    if value is None:
        return None
    return _positive_int(value, field)
