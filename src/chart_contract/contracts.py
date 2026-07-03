"""Shared contract helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

CAUSAL_TERMS = (
    "caused",
    "drove",
    "due to",
    "because of",
    "impact",
    "lift",
)

FILTER_OR_WINDOW_TERMS = (
    "last ",
    "past ",
    "between ",
    "from ",
    "during ",
    "since ",
    "before ",
    "after ",
    "week of",
    "month of",
    "quarter",
    "q1",
    "q2",
    "q3",
    "q4",
)

GENERIC_TITLES = {
    "chart",
    "figure",
    "analysis",
    "results",
    "output",
    "untitled",
}

DECORATIVE_TERMS = (
    "background",
    "image",
    "texture",
    "shadow",
    "depth",
    "3d",
    "extrude",
)


def has_causal_language(text: str | None) -> bool:
    normalized = (text or "").strip().lower()
    return any(term in normalized for term in CAUSAL_TERMS)


def implies_filter_or_time_window(text: str | None) -> bool:
    normalized = (text or "").strip().lower()
    return any(term in normalized for term in FILTER_OR_WINDOW_TERMS)


def has_declared_causal_evidence(metadata: Mapping[str, Any] | None) -> bool:
    return bool(metadata and metadata.get("causal_evidence"))


def is_generic_title(title: str | None) -> bool:
    if not title or not title.strip():
        return True
    normalized = title.strip().lower()
    return normalized in GENERIC_TITLES or normalized.startswith("chart of ")


def is_numeric_series(series: pd.Series) -> bool:
    return bool(pd.api.types.is_numeric_dtype(series))


def is_datetime_like(series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    if pd.api.types.is_numeric_dtype(series):
        # pd.to_datetime() does not raise on plain numbers; it silently
        # coerces them to nanoseconds-since-epoch, which would otherwise
        # cause a false positive here.
        return False
    try:
        pd.to_datetime(series.dropna(), errors="raise")
        return True
    except (TypeError, ValueError):
        return False


def is_ordered_series(series: pd.Series) -> bool:
    dropped = series.dropna()
    if dropped.empty:
        return True
    if is_numeric_series(dropped) or is_datetime_like(dropped):
        return True
    if isinstance(dropped.dtype, pd.CategoricalDtype):
        return bool(dropped.dtype.ordered)
    return bool(dropped.is_monotonic_increasing or dropped.is_monotonic_decreasing)


def find_decorative_terms(payload: Any) -> list[str]:
    found: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, nested in value.items():
                lowered_key = str(key).lower()
                found.update(term for term in DECORATIVE_TERMS if term in lowered_key)
                visit(nested)
            return
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        lowered_value = str(value).lower()
        found.update(term for term in DECORATIVE_TERMS if term in lowered_value)

    visit(payload)
    return sorted(found)


def declared_unit_from_spec(spec: Mapping[str, Any]) -> str | None:
    usermeta = spec.get("usermeta", {})
    if isinstance(usermeta, Mapping):
        unit = usermeta.get("unit")
        if isinstance(unit, str) and unit.strip():
            return unit
    return None


def declared_source_from_spec(spec: Mapping[str, Any]) -> str | None:
    usermeta = spec.get("usermeta", {})
    if isinstance(usermeta, Mapping):
        source = usermeta.get("source")
        if isinstance(source, str) and source.strip():
            return source
    return None


def declared_caveat_from_spec(spec: Mapping[str, Any]) -> str | None:
    usermeta = spec.get("usermeta", {})
    if isinstance(usermeta, Mapping):
        caveat = usermeta.get("caveat")
        if isinstance(caveat, str) and caveat.strip():
            return caveat
    return None


def declared_evidence_from_spec(spec: Mapping[str, Any]) -> bool:
    usermeta = spec.get("usermeta", {})
    return bool(isinstance(usermeta, Mapping) and usermeta.get("causal_evidence"))


def extract_inline_values(spec: Mapping[str, Any]) -> list[dict[str, Any]] | None:
    data = spec.get("data", {})
    if isinstance(data, Mapping):
        values = data.get("values")
        if isinstance(values, list):
            normalized = [item for item in values if isinstance(item, dict)]
            return normalized
    return None
