"""Opt-in source-bound receipts for a restricted Vega-Lite filter subset.

This module intentionally does not evaluate arbitrary Vega expressions.
It supports *only* root-level, sequential field-predicate filters on raw
records. Unsupported predicates, prior transforms, and null/ambiguous
values never produce a source-coverage PASS.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from numbers import Real
from typing import Any

import pandas as pd

from .audit import FAIL, PASS, WARN, AuditReport, _coerce_records
from .transforms import build_transform_lineage

FILTER_IMPACT_KEY = "filter_impact_contract"
FILTER_IMPACT_VERSION = 1
RECEIPTS_RULE = "data.filter.receipts"
RETENTION_RULE = "data.filter.retention"
_MAX_ROWS = 100_000
_MAX_FILTERS = 20
_MAX_ONE_OF = 100
_RECEIPT_KEYS = {
    "location", "operation_sha256", "input_count", "retained_count",
    "excluded_count", "retained_pct",
}
_OPERATORS = ("equal", "oneOf", "gt", "gte", "lt", "lte")


class FilterImpactUnavailable(ValueError):
    """Evidence or filter syntax cannot be reconstructed by this safe subset."""


def _numeric(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, Real):
        return False
    try:
        return math.isfinite(float(value))
    except (ValueError, OverflowError, TypeError):
        return False


def _valid_scalar(value: Any) -> bool:
    return isinstance(value, (str, bool)) or _numeric(value)


def _same_kind(left: Any, right: Any) -> bool:
    if _numeric(left):
        return _numeric(right)
    return type(left) is type(right)


def _predicate(filter_value: Any) -> tuple[str, str, Any]:
    if not isinstance(filter_value, Mapping):
        raise FilterImpactUnavailable(
            "Only structured field predicates are supported; Vega expression strings are not evaluated."
        )
    if set(filter_value) - {"field", *_OPERATORS}:
        raise FilterImpactUnavailable(
            "Filter uses unsupported predicate keys or logical composition."
        )
    field = filter_value.get("field")
    operations = [key for key in _OPERATORS if key in filter_value]
    if not isinstance(field, str) or not field.strip() or len(operations) != 1:
        raise FilterImpactUnavailable(
            "Filter requires one named source field and exactly one supported predicate operator."
        )
    operator = operations[0]
    value = filter_value[operator]
    if operator == "oneOf":
        if (not isinstance(value, list) or not value or len(value) > _MAX_ONE_OF
                or not all(_valid_scalar(item) for item in value)
                or not all(_same_kind(value[0], item) for item in value[1:])):
            raise FilterImpactUnavailable(
                "oneOf requires 1–100 homogeneous finite string, boolean or numeric scalar values."
            )
    elif operator in ("gt", "gte", "lt", "lte"):
        if not _numeric(value):
            raise FilterImpactUnavailable(
                "Ordering predicates require a finite numeric scalar."
            )
    elif not _valid_scalar(value):
        raise FilterImpactUnavailable(
            "Equality predicates require a finite, non-null scalar."
        )
    return field, operator, value


def _filtered(row: Mapping[str, Any], field: str, operator: str, value: Any) -> bool:
    if field not in row:
        raise FilterImpactUnavailable(f"Source field {field!r} is missing.")
    raw = row[field]
    comparison = value[0] if operator == "oneOf" else value
    if not _valid_scalar(raw) or not _same_kind(raw, comparison):
        raise FilterImpactUnavailable(
            f"Field {field!r} contains null/nonfinite or incompatible typed values; "
            "cannot claim complete predicate evaluation."
        )
    if operator == "equal":
        return raw == value
    if operator == "oneOf":
        return raw in value
    if operator == "gt":
        return raw > value
    if operator == "gte":
        return raw >= value
    if operator == "lt":
        return raw < value
    return raw <= value


def _validate_minimum(value: Any) -> float | None:
    if value is None:
        return None
    if not _numeric(value) or not 0 <= value <= 100:
        raise ValueError("filter_impact_contract.minimum_retention_pct must be a finite number from 0 to 100 or null.")
    return float(value)


def parse_filter_impact_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    """Validate the closed v1 input plus claimed receipt fields."""
    meta = spec.get("usermeta")
    if not isinstance(meta, Mapping) or FILTER_IMPACT_KEY not in meta:
        return None
    raw = meta[FILTER_IMPACT_KEY]
    if not isinstance(raw, Mapping) or set(raw) != {
        "version", "minimum_retention_pct", "receipts",
    }:
        raise ValueError("filter_impact_contract requires exactly version, minimum_retention_pct and receipts.")
    if type(raw["version"]) is not int or raw["version"] != FILTER_IMPACT_VERSION:
        raise ValueError("filter_impact_contract.version must equal 1.")
    minimum = _validate_minimum(raw["minimum_retention_pct"])
    receipts = raw["receipts"]
    if not isinstance(receipts, list) or not 1 <= len(receipts) <= _MAX_FILTERS:
        raise ValueError("filter_impact_contract.receipts must contain 1–20 receipts.")
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for receipt in receipts:
        if not isinstance(receipt, Mapping) or set(receipt) != _RECEIPT_KEYS:
            raise ValueError("Each filter-impact receipt must contain exactly the closed v1 receipt fields.")
        location, digest = receipt["location"], receipt["operation_sha256"]
        if not isinstance(location, str) or not location.startswith("transform[") or not location.endswith("].filter") or location in seen:
            raise ValueError("Filter-impact receipt locations must be unique root transform positions.")
        seen.add(location)
        if (not isinstance(digest, str) or len(digest) != 64
                or any(ch not in "0123456789abcdef" for ch in digest)):
            raise ValueError("Filter-impact operation_sha256 must be 64 lowercase hex characters.")
        for field in ("input_count", "retained_count", "excluded_count"):
            if type(receipt[field]) is not int or receipt[field] < 0:
                raise ValueError(f"Filter-impact {field} must be a nonnegative integer.")
        pct = receipt["retained_pct"]
        if not _numeric(pct) or not 0 <= pct <= 100:
            raise ValueError("Filter-impact retained_pct must be a finite number between 0 and 100.")
        if receipt["retained_count"] + receipt["excluded_count"] != receipt["input_count"]:
            raise ValueError("Filter-impact counts do not reconcile.")
        normalized.append(dict(receipt))
    return {"version": FILTER_IMPACT_VERSION, "minimum_retention_pct": minimum, "receipts": normalized}


def _source_rows(
    spec: Mapping[str, Any],
    data: pd.DataFrame | Sequence[Mapping[str, Any]] | None,
) -> list[Mapping[str, Any]]:
    # A root-only filter sequence avoids pretending child-layer datasets and
    # transforms have the same upstream row universe.
    if any(key in spec for key in ("layer", "concat", "hconcat", "vconcat", "spec", "facet", "repeat")):
        raise FilterImpactUnavailable("Only a single root-level view is supported; nested datasets are not reconstructed.")
    transforms = spec.get("transform")
    if not isinstance(transforms, list) or not 1 <= len(transforms) <= _MAX_FILTERS:
        raise FilterImpactUnavailable("Expected 1–20 sequential root-level field filters.")
    for transform in transforms:
        if not isinstance(transform, Mapping) or set(transform) != {"filter"}:
            raise FilterImpactUnavailable(
                "Only filter transforms are supported; an intervening calculation, "
                "aggregation or other operation invalidates raw-row retention receipts."
            )
        _predicate(transform["filter"])
    records = _coerce_records(spec, data)
    if not isinstance(records, list) or not 1 <= len(records) <= _MAX_ROWS:
        raise FilterImpactUnavailable(
            "A nonempty source with at most 100,000 reconstructable rows is required."
        )
    if any(not isinstance(row, Mapping) for row in records):
        raise FilterImpactUnavailable("Source rows must be field-to-value objects.")
    return records


def _recompute(
    spec: Mapping[str, Any],
    data: pd.DataFrame | Sequence[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    rows = _source_rows(spec, data)
    transforms = spec["transform"]
    lineage = {receipt["location"]: receipt["operation_sha256"]
               for receipt in build_transform_lineage(spec)["receipts"]}
    receipts: list[dict[str, Any]] = []
    for index, transform in enumerate(transforms):
        field, operator, value = _predicate(transform["filter"])
        location = f"transform[{index}].filter"
        # Evaluate *every* input row before advancing. A later null or
        # unsupported field cannot be silently ignored after partial counting.
        kept = [row for row in rows if _filtered(row, field, operator, value)]
        total, retained = len(rows), len(kept)
        receipts.append({
            "location": location,
            "operation_sha256": lineage[location],
            "input_count": total,
            "retained_count": retained,
            "excluded_count": total - retained,
            "retained_pct": round(100 * retained / total, 6) if total else 0.0,
        })
        rows = kept
    return receipts


def build_filter_impact_contract(
    spec: Mapping[str, Any],
    data: pd.DataFrame | Sequence[Mapping[str, Any]] | None,
    *,
    minimum_retention_pct: float | None = None,
) -> dict[str, Any]:
    """Build source-recomputed opt-in metadata. Attach under usermeta.

    For unsupported predicates or source evidence, raises
    FilterImpactUnavailable instead of fabricating source receipts.
    """
    minimum = _validate_minimum(minimum_retention_pct)
    return {
        "version": FILTER_IMPACT_VERSION,
        "minimum_retention_pct": minimum,
        "receipts": _recompute(spec, data),
    }


def audit_filter_impact(
    report: AuditReport,
    spec: Mapping[str, Any],
    data: pd.DataFrame | Sequence[Mapping[str, Any]] | None,
) -> None:
    """Verify declared receipts and evaluate the optional retention policy."""
    try:
        declared = parse_filter_impact_contract(spec)
    except ValueError as exc:
        report.add(RECEIPTS_RULE, FAIL, str(exc), field=f"usermeta.{FILTER_IMPACT_KEY}")
        return
    if declared is None:
        return
    try:
        actual = _recompute(spec, data)
    except FilterImpactUnavailable as exc:
        report.add(
            RECEIPTS_RULE, WARN,
            f"Filter retention evidence is unverifiable: {exc}",
            suggestion="Use supported source-bound field predicates or report exclusion counts upstream; never claim a verified receipt for arbitrary expressions.",
            field=f"usermeta.{FILTER_IMPACT_KEY}.receipts",
        )
        if declared["minimum_retention_pct"] is not None:
            report.add(RETENTION_RULE, WARN, "Declared minimum retention was not evaluated because filter evidence is unverifiable.")
        return

    if declared["receipts"] != actual:
        report.add(
            RECEIPTS_RULE, FAIL,
            "Filter-impact receipts do not match source-recomputed operation hashes or row retention counts.",
            suggestion="Regenerate the receipts from the final filters and original source rows; do not edit counts to force PASS.",
            field=f"usermeta.{FILTER_IMPACT_KEY}.receipts",
        )
        return

    start, end = actual[0]["input_count"], actual[-1]["retained_count"]
    percent = 100 * end / start
    report.add(
        RECEIPTS_RULE, PASS,
        f"Verified {len(actual)} sequential filter receipt(s): "
        f"{start} input row(s), {end} retained, {start - end} excluded "
        f"({percent:.2f}% retained overall).",
        field=f"usermeta.{FILTER_IMPACT_KEY}.receipts",
    )
    minimum = declared["minimum_retention_pct"]
    if minimum is not None and percent < minimum:
        report.add(
            RETENTION_RULE, WARN,
            f"Filter retains {end} of {start} source row(s) ({percent:.2f}%), "
            f"below declared minimum {minimum:g}% ({start - end} excluded).",
            suggestion="Check whether exclusions match the claimed population; revise the explicitly declared minimum only with operator approval.",
            field=f"usermeta.{FILTER_IMPACT_KEY}.minimum_retention_pct",
        )
    else:
        note = (
            f"meets declared minimum {minimum:g}%."
            if minimum is not None else
            "no minimum retention threshold was declared (descriptive only)."
        )
        report.add(
            RETENTION_RULE, PASS,
            f"Filter retains {end} of {start} source row(s) ({percent:.2f}%); {note}",
            field=f"usermeta.{FILTER_IMPACT_KEY}.minimum_retention_pct",
        )
