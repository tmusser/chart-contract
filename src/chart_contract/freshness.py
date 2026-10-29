"""Opt-in deterministic freshness/finalization contract for descriptive charts.

The comparison clock is explicitly declared, never inferred from the host.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

import pandas as pd

FRESHNESS_CONTRACT_KEY = "freshness_contract"
FRESHNESS_INTENTS = {"trend", "rank", "compare"}
_INPUT_FIELDS = {
    "version", "audit_date", "observation_date_field",
    "finalized_through", "max_age_days", "require_finalized",
}
_RECEIPT_FIELDS = {"data_through", "row_count"}


def canonical_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"Freshness {field} must be an ISO YYYY-MM-DD string.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Freshness {field} must be an ISO YYYY-MM-DD string.") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"Freshness {field} must use canonical ISO YYYY-MM-DD format.")
    return parsed


def freshness_declaration(chart: Any) -> dict[str, Any] | None:
    field_names = (
        "freshness_audit_date", "freshness_observation_date_field",
        "freshness_finalized_through", "freshness_max_age_days",
        "freshness_require_finalized",
    )
    values = [getattr(chart, name, None) for name in field_names]
    if all(value is None for value in values):
        return None
    return {
        "version": 1,
        "audit_date": values[0],
        "observation_date_field": values[1],
        "finalized_through": values[2],
        "max_age_days": values[3],
        "require_finalized": values[4],
    }


def validate_declaration(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) != _INPUT_FIELDS:
        raise ValueError("Freshness declaration requires exactly the closed v1 input fields.")
    if type(raw["version"]) is not int or raw["version"] != 1:
        raise ValueError("Freshness contract version must equal 1.")
    audit = canonical_date(raw["audit_date"], "audit_date")
    finalized = canonical_date(raw["finalized_through"], "finalized_through")
    field = raw["observation_date_field"]
    if not isinstance(field, str) or not field.strip():
        raise ValueError("Freshness observation_date_field must be a non-empty string.")
    if type(raw["max_age_days"]) is not int or raw["max_age_days"] < 0:
        raise ValueError("Freshness max_age_days must be a non-negative integer.")
    if type(raw["require_finalized"]) is not bool:
        raise ValueError("Freshness require_finalized must be a boolean.")
    if finalized > audit:
        raise ValueError("Freshness finalized_through cannot be after audit_date.")
    return dict(raw)


def build_freshness_contract(frame: pd.DataFrame, declaration: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute latest observation and row count, without mutating evidence."""
    meta = validate_declaration(declaration)
    field = meta["observation_date_field"]
    if field not in frame.columns:
        raise ValueError(f"Freshness observation date field {field!r} is missing from supplied evidence.")
    if frame.empty:
        raise ValueError("Freshness requires at least one supplied observation.")
    dates = []
    for index, raw in enumerate(frame[field].tolist(), 1):
        try:
            dates.append(canonical_date(raw, f"row {index} observation date"))
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
    latest = max(dates)
    return {
        **meta,
        "data_through": latest.isoformat(),
        "row_count": len(dates),
    }


def parse_freshness_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    meta = spec.get("usermeta")
    if not isinstance(meta, Mapping) or FRESHNESS_CONTRACT_KEY not in meta:
        return None
    raw = meta[FRESHNESS_CONTRACT_KEY]
    if not isinstance(raw, Mapping) or set(raw) != _INPUT_FIELDS | _RECEIPT_FIELDS:
        raise ValueError("usermeta.freshness_contract requires the exact closed v1 fields.")
    inputs = validate_declaration({key: raw[key] for key in _INPUT_FIELDS})
    canonical_date(raw["data_through"], "data_through")
    if type(raw["row_count"]) is not int or raw["row_count"] < 1:
        raise ValueError("Freshness row_count receipt must be a positive integer.")
    return {**inputs, "data_through": raw["data_through"], "row_count": raw["row_count"]}


def freshness_status(contract: Mapping[str, Any]) -> tuple[tuple[bool, str], tuple[str, str]]:
    """Return freshness gate and finalized-data gate for verified receipts."""
    audit = canonical_date(contract["audit_date"], "audit_date")
    latest = canonical_date(contract["data_through"], "data_through")
    finalized = canonical_date(contract["finalized_through"], "finalized_through")
    age = (audit - latest).days
    if age < 0:
        freshness = (False, "Future-dated observation extends past the declared audit date.")
    elif age > contract["max_age_days"]:
        freshness = (
            False, f"Stale data: latest observation {latest.isoformat()} is {age} days old "
            f"as of {audit.isoformat()}, exceeding max_age_days={contract['max_age_days']}.",
        )
    else:
        freshness = (
            True, f"Freshness age {age} day(s) is within "
            f"max_age_days={contract['max_age_days']}.",
        )

    if latest <= finalized:
        final = ("PASS", "All supplied observations fall on or before finalized_through.")
    elif contract["require_finalized"]:
        final = (
            "FAIL", f"Preliminary data: latest observation {latest.isoformat()} is after "
            f"finalized_through={finalized.isoformat()} and finalized evidence is required.",
        )
    else:
        final = (
            "WARN", f"Preliminary data: latest observation {latest.isoformat()} is after "
            f"finalized_through={finalized.isoformat()}; finalization is not required.",
        )
    return freshness, final
