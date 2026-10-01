"""Deterministic inventory helpers for explicit Vega-Lite analytical transforms."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any

TRANSFORM_CONTRACT_KEY = "transform_contract"

# Explicit Vega-Lite transform operators. Keep this list bounded and inspectable rather
# than treating arbitrary object keys as analytical semantics.
TRANSFORM_KINDS = (
    "aggregate",
    "bin",
    "calculate",
    "density",
    "extent",
    "filter",
    "flatten",
    "fold",
    "impute",
    "joinaggregate",
    "loess",
    "lookup",
    "pivot",
    "quantile",
    "regression",
    "sample",
    "stack",
    "timeUnit",
    "window",
)

ENCODING_TRANSFORM_KINDS = ("aggregate", "bin", "stack", "timeUnit")

_AGGREGATE_SHORTHAND = {
    "argmax",
    "argmin",
    "average",
    "ci0",
    "ci1",
    "count",
    "distinct",
    "max",
    "mean",
    "median",
    "min",
    "missing",
    "product",
    "q1",
    "q3",
    "stderr",
    "stdev",
    "stdevp",
    "sum",
    "valid",
    "variance",
    "variancep",
}
_TIMEUNIT_SHORTHAND = {
    "year",
    "quarter",
    "month",
    "week",
    "day",
    "dayofyear",
    "date",
    "hours",
    "minutes",
    "seconds",
    "milliseconds",
    "yearquarter",
    "yearquartermonth",
    "yearmonth",
    "yearmonthdate",
    "yearmonthdatehours",
    "yearmonthdatehoursminutes",
    "yearmonthdatehoursminutesseconds",
    "monthdate",
    "hoursminutes",
    "hoursminutesseconds",
    "minutesseconds",
    "secondsmilliseconds",
}
_SHORTHAND_CALL_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)\([^)]*\)(?::[A-Za-z])?$")


@dataclass(frozen=True, slots=True)
class TransformOccurrence:
    kind: str
    location: str
    source: str


@dataclass(frozen=True, slots=True)
class TransformInventory:
    occurrences: tuple[TransformOccurrence, ...]
    malformed_locations: tuple[str, ...]

    @property
    def kinds(self) -> tuple[str, ...]:
        return tuple(sorted({occurrence.kind for occurrence in self.occurrences}))


def collect_transform_inventory(spec: Mapping[str, Any]) -> TransformInventory:
    """Collect explicit transform semantics without executing or interpreting expressions."""

    occurrences: list[TransformOccurrence] = []
    malformed: list[str] = []

    for view_path, view in _iter_views_with_paths(spec):
        transforms = view.get("transform")
        if transforms is not None:
            transform_path = _path(view_path, "transform")
            if not isinstance(transforms, list):
                malformed.append(transform_path)
            else:
                for index, transform in enumerate(transforms):
                    location = f"{transform_path}[{index}]"
                    if not isinstance(transform, Mapping):
                        malformed.append(location)
                        continue

                    kinds = [kind for kind in TRANSFORM_KINDS if kind in transform]
                    if len(kinds) != 1:
                        malformed.append(location)
                    for kind in kinds:
                        occurrences.append(
                            TransformOccurrence(
                                kind=kind,
                                location=f"{location}.{kind}",
                                source="transform",
                            )
                        )

        encoding = view.get("encoding")
        if not isinstance(encoding, Mapping):
            continue

        for channel, definition in encoding.items():
            definitions = definition if isinstance(definition, list) else [definition]
            for index, item in enumerate(definitions):
                suffix = f"[{index}]" if isinstance(definition, list) else ""
                channel_path = _path(view_path, f"encoding.{channel}{suffix}")
                if isinstance(item, Mapping):
                    for kind in ENCODING_TRANSFORM_KINDS:
                        if _encoding_transform_present(kind, item):
                            occurrences.append(
                                TransformOccurrence(
                                    kind=kind,
                                    location=f"{channel_path}.{kind}",
                                    source="encoding",
                                )
                            )
                elif isinstance(item, str):
                    shorthand_kind = _shorthand_transform_kind(item)
                    if shorthand_kind is not None:
                        occurrences.append(
                            TransformOccurrence(
                                kind=shorthand_kind,
                                location=channel_path,
                                source="encoding_shorthand",
                            )
                        )

    unique_occurrences = tuple(
        sorted(
            set(occurrences),
            key=lambda occurrence: (
                occurrence.location,
                occurrence.kind,
                occurrence.source,
            ),
        )
    )
    return TransformInventory(
        occurrences=unique_occurrences,
        malformed_locations=tuple(sorted(set(malformed))),
    )


def parse_transform_declaration(spec: Mapping[str, Any]) -> tuple[str, ...] | None:
    """Parse a closed transform declaration or raise ValueError for malformed metadata."""

    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or TRANSFORM_CONTRACT_KEY not in usermeta:
        return None

    contract = usermeta.get(TRANSFORM_CONTRACT_KEY)
    if not isinstance(contract, Mapping):
        raise ValueError("usermeta.transform_contract must be an object.")

    unexpected = sorted(set(contract) - {"declared"})
    if unexpected:
        raise ValueError(
            "usermeta.transform_contract has unsupported field(s): "
            + ", ".join(str(field) for field in unexpected)
        )

    declared = contract.get("declared")
    if not isinstance(declared, list):
        raise ValueError("usermeta.transform_contract.declared must be a list.")

    normalized: list[str] = []
    for value in declared:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "usermeta.transform_contract.declared entries must be non-empty strings."
            )
        kind = value.strip()
        if kind not in TRANSFORM_KINDS:
            raise ValueError(f"Unsupported declared transform kind: {kind!r}.")
        normalized.append(kind)

    if len(normalized) != len(set(normalized)):
        raise ValueError("usermeta.transform_contract.declared must not contain duplicates.")

    return tuple(sorted(normalized))


def first_party_transform_declaration(intent: str) -> tuple[str, ...]:
    """Return explicit transform kinds emitted by a first-party renderer."""

    if intent == "histogram":
        return ("aggregate", "bin")
    if intent == "violin":
        return ("density",)
    return ()


def _iter_views_with_paths(
    spec: Mapping[str, Any],
    path: str = "",
) -> Iterator[tuple[str, Mapping[str, Any]]]:
    yield path, spec

    for collection_key in ("layer", "concat", "hconcat", "vconcat"):
        nested = spec.get(collection_key)
        if not isinstance(nested, list):
            continue
        for index, item in enumerate(nested):
            if isinstance(item, Mapping):
                child_path = _path(path, f"{collection_key}[{index}]")
                yield from _iter_views_with_paths(item, child_path)

    nested_spec = spec.get("spec")
    if isinstance(nested_spec, Mapping):
        yield from _iter_views_with_paths(nested_spec, _path(path, "spec"))


def _encoding_transform_present(kind: str, definition: Mapping[str, Any]) -> bool:
    if kind not in definition:
        return False
    value = definition.get(kind)
    if kind == "bin":
        return value not in (None, False)
    if kind == "stack":
        return value not in (None, False)
    return value is not None


def _shorthand_transform_kind(definition: str) -> str | None:
    text = definition.strip()
    match = _SHORTHAND_CALL_RE.match(text)
    if match is None:
        return None
    operator = match.group(1)
    if operator in _AGGREGATE_SHORTHAND:
        return "aggregate"
    if operator == "bin":
        return "bin"
    if operator in _TIMEUNIT_SHORTHAND:
        return "timeUnit"
    return None


def _path(prefix: str, suffix: str) -> str:
    return f"{prefix}.{suffix}" if prefix else suffix
