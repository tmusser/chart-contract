"""Deterministic inventory helpers for explicit Vega-Lite analytical transforms."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any

TRANSFORM_CONTRACT_KEY = "transform_contract"
TRANSFORM_LINEAGE_KEY = "transform_lineage"
TRANSFORM_LINEAGE_VERSION = 1

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
class TransformReceipt:
    kind: str
    location: str
    operation_sha256: str
    input_fields: tuple[str, ...]
    output_fields: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "location": self.location,
            "operation_sha256": self.operation_sha256,
            "input_fields": list(self.input_fields),
            "output_fields": list(self.output_fields),
        }


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

                    kinds = _explicit_transform_kinds(transform)
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


def build_transform_lineage(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Build deterministic structural receipts for explicit Vega-Lite transformations."""

    receipts: list[TransformReceipt] = []
    for view_path, view in _iter_views_with_paths(spec):
        transforms = view.get("transform")
        if isinstance(transforms, list):
            transform_path = _path(view_path, "transform")
            for index, transform in enumerate(transforms):
                if not isinstance(transform, Mapping):
                    continue
                kinds = _explicit_transform_kinds(transform)
                if len(kinds) != 1:
                    continue
                kind = kinds[0]
                location = f"{transform_path}[{index}].{kind}"
                inputs, outputs = _transform_fields(kind, transform)
                receipts.append(
                    TransformReceipt(
                        kind=kind,
                        location=location,
                        operation_sha256=_sha256_json(dict(transform)),
                        input_fields=tuple(sorted(inputs)),
                        output_fields=tuple(sorted(outputs)),
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
                    field = item.get("field") if isinstance(item.get("field"), str) else None
                    for kind in ENCODING_TRANSFORM_KINDS:
                        if not _encoding_transform_present(kind, item):
                            continue
                        payload = {
                            "field": field,
                            kind: item.get(kind),
                        }
                        receipts.append(
                            TransformReceipt(
                                kind=kind,
                                location=f"{channel_path}.{kind}",
                                operation_sha256=_sha256_json(payload),
                                input_fields=(field,) if field else (),
                                output_fields=(),
                            )
                        )
                elif isinstance(item, str):
                    kind = _shorthand_transform_kind(item)
                    if kind is None:
                        continue
                    shorthand = _encoding_shorthand_parts(item)
                    field = shorthand[1] if shorthand is not None else None
                    receipts.append(
                        TransformReceipt(
                            kind=kind,
                            location=channel_path,
                            operation_sha256=_sha256_json({"shorthand": item.strip()}),
                            input_fields=(field,) if field else (),
                            output_fields=(),
                        )
                    )

    ordered = sorted(receipts, key=lambda receipt: (receipt.location, receipt.kind))
    return {
        "version": TRANSFORM_LINEAGE_VERSION,
        "receipts": [receipt.to_dict() for receipt in ordered],
    }


def parse_transform_lineage(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    """Parse and validate transform lineage metadata as a closed schema."""

    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or TRANSFORM_LINEAGE_KEY not in usermeta:
        return None

    lineage = usermeta.get(TRANSFORM_LINEAGE_KEY)
    if not isinstance(lineage, Mapping):
        raise ValueError("usermeta.transform_lineage must be an object.")

    unexpected = sorted(str(field) for field in lineage if field not in {"version", "receipts"})
    if unexpected:
        raise ValueError(
            "usermeta.transform_lineage has unsupported field(s): " + ", ".join(unexpected)
        )
    if lineage.get("version") != TRANSFORM_LINEAGE_VERSION:
        raise ValueError(
            f"usermeta.transform_lineage.version must equal {TRANSFORM_LINEAGE_VERSION}."
        )
    receipts = lineage.get("receipts")
    if not isinstance(receipts, list):
        raise ValueError("usermeta.transform_lineage.receipts must be a list.")

    normalized: list[dict[str, Any]] = []
    seen_locations: set[str] = set()
    for receipt in receipts:
        if not isinstance(receipt, Mapping):
            raise ValueError("Each transform lineage receipt must be an object.")
        if set(receipt) != {
            "kind",
            "location",
            "operation_sha256",
            "input_fields",
            "output_fields",
        }:
            raise ValueError(
                "Each transform lineage receipt must contain exactly kind, location, "
                "operation_sha256, input_fields, and output_fields."
            )
        kind = receipt.get("kind")
        location = receipt.get("location")
        operation_sha256 = receipt.get("operation_sha256")
        input_fields = receipt.get("input_fields")
        output_fields = receipt.get("output_fields")
        if kind not in TRANSFORM_KINDS:
            raise ValueError(f"Unsupported lineage transform kind: {kind!r}.")
        if not isinstance(location, str) or not location:
            raise ValueError("Transform lineage receipt location must be a non-empty string.")
        if location in seen_locations:
            raise ValueError("Transform lineage receipt locations must be unique.")
        seen_locations.add(location)
        if (
            not isinstance(operation_sha256, str)
            or len(operation_sha256) != 64
            or any(ch not in "0123456789abcdef" for ch in operation_sha256)
        ):
            raise ValueError("Transform lineage operation_sha256 must be 64 lowercase hex characters.")
        for name, values in (("input_fields", input_fields), ("output_fields", output_fields)):
            if not isinstance(values, list) or any(
                not isinstance(value, str) or not value for value in values
            ):
                raise ValueError(f"Transform lineage {name} must be a list of non-empty strings.")
            if values != sorted(set(values)):
                raise ValueError(f"Transform lineage {name} must be sorted and unique.")
        normalized.append(
            {
                "kind": kind,
                "location": location,
                "operation_sha256": operation_sha256,
                "input_fields": list(input_fields),
                "output_fields": list(output_fields),
            }
        )

    normalized.sort(key=lambda receipt: (receipt["location"], receipt["kind"]))
    return {"version": TRANSFORM_LINEAGE_VERSION, "receipts": normalized}


def parse_transform_declaration(spec: Mapping[str, Any]) -> tuple[str, ...] | None:
    """Parse a closed transform declaration or raise ValueError for malformed metadata."""

    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or TRANSFORM_CONTRACT_KEY not in usermeta:
        return None

    contract = usermeta.get(TRANSFORM_CONTRACT_KEY)
    if not isinstance(contract, Mapping):
        raise ValueError("usermeta.transform_contract must be an object.")

    unexpected = sorted(str(field) for field in contract if field != "declared")
    if unexpected:
        raise ValueError(
            "usermeta.transform_contract has unsupported field(s): "
            + ", ".join(unexpected)
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


def _explicit_transform_kinds(transform: Mapping[str, Any]) -> list[str]:
    kinds = [kind for kind in TRANSFORM_KINDS if kind in transform]

    # Vega-Lite density uses an optional top-level "extent" parameter, while
    # {"extent": "field", "param": "..."} is also a standalone extent transform.
    # When density is present, extent describes density bounds rather than a
    # second transform operator.
    if "density" in kinds and "extent" in kinds:
        kinds.remove("extent")

    return kinds


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


def _transform_fields(kind: str, transform: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    inputs: set[str] = set()
    outputs: set[str] = set()

    def add_field(value: Any) -> None:
        if isinstance(value, str) and value:
            inputs.add(value)

    def add_fields(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                add_field(item)

    def add_outputs(value: Any) -> None:
        if isinstance(value, str) and value:
            outputs.add(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item:
                    outputs.add(item)

    if kind in {"aggregate", "joinaggregate", "window"}:
        ops = transform.get(kind)
        if isinstance(ops, list):
            for op in ops:
                if isinstance(op, Mapping):
                    add_field(op.get("field"))
                    add_outputs(op.get("as"))
        add_fields(transform.get("groupby"))
    elif kind == "calculate":
        expression = transform.get("calculate")
        if isinstance(expression, str):
            inputs.update(_expression_fields(expression))
        add_outputs(transform.get("as"))
    elif kind == "filter":
        predicate = transform.get("filter")
        if isinstance(predicate, str):
            inputs.update(_expression_fields(predicate))
        else:
            inputs.update(_predicate_fields(predicate))
    elif kind == "density":
        add_field(transform.get("density"))
        add_fields(transform.get("groupby"))
        add_outputs(transform.get("as"))
    elif kind == "extent":
        add_field(transform.get("extent"))
    elif kind in {"flatten", "fold"}:
        add_fields(transform.get(kind))
        add_outputs(transform.get("as"))
    elif kind == "impute":
        add_field(transform.get("impute"))
        add_field(transform.get("key"))
        add_fields(transform.get("groupby"))
        add_outputs(transform.get("impute"))
    elif kind == "lookup":
        add_field(transform.get("lookup"))
        add_outputs(transform.get("as"))
    elif kind == "pivot":
        add_field(transform.get("pivot"))
        add_field(transform.get("value"))
        add_fields(transform.get("groupby"))
    elif kind == "quantile":
        add_field(transform.get("quantile"))
        add_fields(transform.get("groupby"))
        add_outputs(transform.get("as"))
    elif kind in {"regression", "loess"}:
        add_field(transform.get(kind))
        add_field(transform.get("on"))
        add_fields(transform.get("groupby"))
        add_outputs(transform.get("as"))
    elif kind == "stack":
        add_field(transform.get("stack"))
        add_fields(transform.get("groupby"))
        sort = transform.get("sort")
        if isinstance(sort, list):
            for item in sort:
                if isinstance(item, Mapping):
                    add_field(item.get("field"))
        add_outputs(transform.get("as"))
    elif kind == "timeUnit":
        add_field(transform.get("field"))
        add_outputs(transform.get("as"))

    return inputs, outputs


_EXPRESSION_DOT_RE = re.compile(r"\bdatum\.([A-Za-z_][A-Za-z0-9_]*)")
_EXPRESSION_BRACKET_RE = re.compile(r"""\bdatum\[['"]([^'"]+)['"]\]""")


def _expression_fields(expression: str) -> set[str]:
    return set(_EXPRESSION_DOT_RE.findall(expression)) | set(_EXPRESSION_BRACKET_RE.findall(expression))


def _predicate_fields(payload: Any) -> set[str]:
    fields: set[str] = set()
    if isinstance(payload, Mapping):
        field = payload.get("field")
        if isinstance(field, str) and field:
            fields.add(field)
        for value in payload.values():
            fields.update(_predicate_fields(value))
    elif isinstance(payload, list):
        for value in payload:
            fields.update(_predicate_fields(value))
    return fields


def _encoding_shorthand_parts(definition: str) -> tuple[str, str | None] | None:
    text = definition.strip()
    match = _SHORTHAND_CALL_RE.match(text)
    if match is None:
        return None
    operator = match.group(1)
    open_paren = text.find("(")
    close_paren = text.rfind(")")
    field = text[open_paren + 1 : close_paren].strip() if open_paren >= 0 and close_paren > open_paren else ""
    return operator, field or None


def _sha256_json(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _path(prefix: str, suffix: str) -> str:
    return f"{prefix}.{suffix}" if prefix else suffix
