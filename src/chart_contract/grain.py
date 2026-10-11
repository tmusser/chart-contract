"""Deterministic source-grain and aggregation contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

GRAIN_CONTRACT_KEY = "grain_contract"
GRAIN_CONTRACT_VERSION = 1
GRAIN_INTENTS = {"trend", "rank", "compare"}
SUPPORTED_AGGREGATIONS = {"sum", "mean", "median", "min", "max", "count", "distinct"}


@dataclass(frozen=True, slots=True)
class GrainSummary:
    source_grain_fields: tuple[str, ...]
    output_grain_fields: tuple[str, ...]
    aggregation: dict[str, str] | None
    source_row_count: int
    source_unique_grain_count: int
    output_group_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": GRAIN_CONTRACT_VERSION,
            "source_grain_fields": list(self.source_grain_fields),
            "output_grain_fields": list(self.output_grain_fields),
            "aggregation": self.aggregation,
            "source_row_count": self.source_row_count,
            "source_unique_grain_count": self.source_unique_grain_count,
            "output_group_count": self.output_group_count,
        }


def normalize_grain_fields(values: Any, *, field_name: str = "grain_fields") -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError(f"{field_name} must be a non-empty list/tuple of field names.")
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} entries must be non-empty strings.")
        normalized.append(value.strip())
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{field_name} entries must be unique.")
    return tuple(sorted(normalized))


def visible_grain_fields_for_chart(chart: Any) -> tuple[str, ...]:
    fields: list[str] = []
    if getattr(chart, "intent", None) in GRAIN_INTENTS and getattr(chart, "x", None):
        fields.append(chart.x)
    if getattr(chart, "intent", None) == "compare" and getattr(chart, "group", None):
        fields.append(chart.group)
    return tuple(sorted(set(fields)))


def build_grain_summary(
    frame: pd.DataFrame,
    *,
    source_grain_fields: Sequence[str],
    output_grain_fields: Sequence[str],
    aggregation: Mapping[str, Any] | None = None,
) -> GrainSummary:
    source_fields = normalize_grain_fields(list(source_grain_fields), field_name="source_grain_fields")
    output_fields = normalize_grain_fields(list(output_grain_fields), field_name="output_grain_fields")
    missing = sorted((set(source_fields) | set(output_fields)) - set(frame.columns))
    if missing:
        raise ValueError("Grain contract references missing field(s): " + ", ".join(missing) + ".")

    for field in source_fields:
        if frame[field].isna().any():
            raise ValueError(f"Source grain field {field!r} contains null values.")

    duplicated = frame.duplicated(subset=list(source_fields), keep=False)
    if duplicated.any():
        duplicate_rows = int(duplicated.sum())
        raise ValueError(
            f"Declared source grain {list(source_fields)!r} is not unique; "
            f"{duplicate_rows} rows participate in duplicate grain keys."
        )

    normalized_aggregation = normalize_aggregation(aggregation)
    output_group_count = int(frame.groupby(list(output_fields), dropna=False).ngroups) if len(frame) else 0
    if normalized_aggregation is None and output_group_count != len(frame):
        raise ValueError(
            "Multiple unique source-grain rows map to the same displayed grain, "
            "but no explicit aggregation is declared."
        )

    return GrainSummary(
        source_grain_fields=source_fields,
        output_grain_fields=output_fields,
        aggregation=normalized_aggregation,
        source_row_count=int(len(frame)),
        source_unique_grain_count=int(len(frame)),
        output_group_count=output_group_count,
    )


def parse_grain_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or GRAIN_CONTRACT_KEY not in usermeta:
        return None
    contract = usermeta.get(GRAIN_CONTRACT_KEY)
    if not isinstance(contract, Mapping):
        raise ValueError("usermeta.grain_contract must be an object.")

    expected = {
        "version",
        "source_grain_fields",
        "output_grain_fields",
        "aggregation",
        "source_row_count",
        "source_unique_grain_count",
        "output_group_count",
    }
    if set(contract) != expected:
        missing = sorted(expected - set(contract))
        extra = sorted(set(contract) - expected)
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("unsupported: " + ", ".join(extra))
        raise ValueError(
            "usermeta.grain_contract must use the exact v1 field set"
            + (" (" + "; ".join(details) + ")" if details else "")
            + "."
        )
    if contract.get("version") != GRAIN_CONTRACT_VERSION:
        raise ValueError(f"usermeta.grain_contract.version must equal {GRAIN_CONTRACT_VERSION}.")

    source_fields = normalize_grain_fields(
        contract.get("source_grain_fields"),
        field_name="usermeta.grain_contract.source_grain_fields",
    )
    output_fields = normalize_grain_fields(
        contract.get("output_grain_fields"),
        field_name="usermeta.grain_contract.output_grain_fields",
    )
    aggregation = normalize_aggregation(contract.get("aggregation"))

    counts: dict[str, int] = {}
    for name in ("source_row_count", "source_unique_grain_count", "output_group_count"):
        value = contract.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"usermeta.grain_contract.{name} must be a non-negative integer.")
        counts[name] = value
    if counts["source_unique_grain_count"] > counts["source_row_count"]:
        raise ValueError("source_unique_grain_count cannot exceed source_row_count.")
    if counts["output_group_count"] > counts["source_unique_grain_count"]:
        raise ValueError("output_group_count cannot exceed source_unique_grain_count.")

    return {
        "version": GRAIN_CONTRACT_VERSION,
        "source_grain_fields": list(source_fields),
        "output_grain_fields": list(output_fields),
        "aggregation": aggregation,
        **counts,
    }


def normalize_aggregation(value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping) or set(value) != {"op", "field"}:
        raise ValueError("grain aggregation must contain exactly 'op' and 'field'.")
    op = value.get("op")
    field = value.get("field")
    if not isinstance(op, str) or op not in SUPPORTED_AGGREGATIONS:
        raise ValueError(
            "grain aggregation op must be one of " + ", ".join(sorted(SUPPORTED_AGGREGATIONS)) + "."
        )
    if not isinstance(field, str) or not field.strip():
        raise ValueError("grain aggregation field must be a non-empty string.")
    return {"op": op, "field": field.strip()}


def visible_grain_fields_from_encoding(encoding: Any) -> tuple[str, ...]:
    if not isinstance(encoding, Mapping):
        return ()
    fields: set[str] = set()
    for channel in ("x", "y", "color", "xOffset", "yOffset", "row", "column", "detail"):
        definition = encoding.get(channel)
        definitions = definition if isinstance(definition, list) else [definition]
        for item in definitions:
            if not isinstance(item, Mapping):
                continue
            field = item.get("field")
            type_name = item.get("type")
            if isinstance(field, str) and type_name != "quantitative":
                fields.add(field)
    return tuple(sorted(fields))


def encoding_aggregation(encoding: Any) -> dict[str, str] | None:
    """Return one bounded encoding-level aggregation, or raise on unsupported ambiguity."""

    if not isinstance(encoding, Mapping):
        return None
    found: list[dict[str, str]] = []
    for definition in encoding.values():
        definitions = definition if isinstance(definition, list) else [definition]
        for item in definitions:
            if not isinstance(item, Mapping) or "aggregate" not in item:
                continue
            op = item.get("aggregate")
            field = item.get("field")
            if op == "count" and field is None:
                field = "*"
            if not isinstance(op, str) or op not in SUPPORTED_AGGREGATIONS:
                raise ValueError(f"Unsupported grain aggregation operator: {op!r}.")
            if not isinstance(field, str) or not field:
                raise ValueError("Encoding aggregation must identify an input field.")
            found.append({"op": op, "field": field})
    unique = {(entry["op"], entry["field"]) for entry in found}
    if len(unique) > 1:
        raise ValueError("Version-1 grain contracts support at most one aggregate metric operation.")
    return found[0] if found else None
