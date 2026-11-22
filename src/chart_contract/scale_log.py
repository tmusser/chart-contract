"""Check log-axis mathematical domains against directly plotted source evidence.

This is a visibility/integrity gate, not a renderer or a statistical analysis.
Vega-Lite permits *negative-only* log domains; only zero or signs that cannot
share the axis's declared domain are mathematically unrepresentable.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from .audit import FAIL, PASS, WARN, AuditReport, _coerce_records
from .scale_clipping import (
    _SUPPORTED_MARKS,
    _UNSUPPORTED_TRANSFORM_KEYS,
    _finite_number,
    _iter_views,
    _mark_type,
    _nested_or_transformed,
    _visible_pairs,
)

RULE = "visual.scale.log_domain"


def _log_axes(view: Mapping[str, Any]):
    """Only actual quantitative x/y axes with explicit log scale types."""
    encoding = view.get("encoding")
    if not isinstance(encoding, Mapping):
        return
    for axis in ("x", "y"):
        definition = encoding.get(axis)
        if not isinstance(definition, Mapping) or definition.get("type") not in ("quantitative", "Q"):
            continue
        scale = definition.get("scale")
        if isinstance(scale, Mapping) and scale.get("type") == "log":
            yield axis, definition, scale


def _declared_domain_sign(scale: Mapping[str, Any]) -> tuple[int | None, str | None, str | None]:
    """Return (required sign, invalid reason, unverifiable reason).

    +1 means a strictly positive domain, -1 strictly negative.
    Unknown scale expressions never establish a coverage PASS.
    """
    if "domainRaw" in scale:
        return None, None, "dynamic domainRaw prevents checking the resulting log domain"
    if "domain" in scale and any(k in scale for k in ("domainMin", "domainMax")):
        return None, None, "combined domain and domainMin/domainMax have ambiguous precedence"
    if "domain" in scale:
        declared = scale["domain"]
        if not isinstance(declared, (list, tuple)) or len(declared) != 2:
            return None, None, "unsupported or malformed explicit log domain"
        low, high = (_finite_number(value) for value in declared)
        if low is None or high is None:
            return None, None, "nonfinite or nonnumeric explicit log domain"
    else:
        raw_low = scale.get("domainMin")
        raw_high = scale.get("domainMax")
        low = _finite_number(raw_low) if "domainMin" in scale else None
        high = _finite_number(raw_high) if "domainMax" in scale else None
        if ("domainMin" in scale and low is None) or ("domainMax" in scale and high is None):
            return None, None, "nonnumeric explicit log-domain boundary"

    if low == 0 or high == 0:
        return None, "explicit log-domain bound includes zero", None
    if low is not None and high is not None:
        if low * high < 0:
            return None, "explicit log domain crosses zero", None
        if low >= high:
            return None, None, "log-domain bounds are reversed or equal"
        return (1 if low > 0 else -1), None, None
    if low is not None and low > 0:
        return 1, None, None
    if high is not None and high < 0:
        return -1, None, None
    if low is not None or high is not None:
        return None, None, "partial log-domain bounds do not establish a single sign"
    return None, None, None


def _find_values(
    spec: Mapping[str, Any],
    data: pd.DataFrame | Sequence[Mapping[str, Any]] | None,
    *,
    axis: str, definition: Mapping[str, Any],
    records: list[Mapping[str, Any]] | None,
) -> tuple[list[float], int, str | None]:
    field = definition.get("field")
    if not isinstance(field, str) or not field.strip():
        return [], 0, "no direct source field is encoded"
    if not records:
        return [], 0, "source observations are unavailable"
    if any(not isinstance(row, Mapping) or field not in row for row in records):
        return [], 0, f"source field {field!r} is missing from at least one row"
    values, skipped = _visible_pairs(records, spec["encoding"], axis, field)
    if not values:
        return [], skipped, "there are no finite directly plotted observations"
    return values, skipped, None


def audit_log_scale(
    report: AuditReport,
    spec: Mapping[str, Any],
    data: pd.DataFrame | Sequence[Mapping[str, Any]] | None,
) -> None:
    """Fail definite log-domain contradictions; review unverifiable cases.

    Findings are emitted once for each x/y channel with an explicit log scale.
    No finding for linear, symlog, temporal, or categorical scales.
    """
    views = list(_iter_views(spec))
    candidates = [
        (view, axis, definition, scale)
        for view in views
        for axis, definition, scale in _log_axes(view)
    ]
    if not candidates:
        return

    simple = (
        len(views) == 1
        and not _nested_or_transformed(spec)
        and _mark_type(spec) in _SUPPORTED_MARKS
        and isinstance(spec.get("encoding"), Mapping)
    )
    records = _coerce_records(spec, data) if simple else None

    for view, axis, definition, scale in candidates:
        field = definition.get("field")
        label = f"encoding.{axis}.scale"
        sign, bad_domain, unknown_domain = _declared_domain_sign(scale)

        if bad_domain:
            report.add(
                RULE, FAIL, f"Quantitative {axis} log scale is invalid: {bad_domain}.",
                suggestion="Declare a strictly positive or strictly negative nonzero log domain.",
                field=label,
            )
            continue

        if not simple or view is not spec:
            report.add(
                RULE, WARN,
                f"Cannot verify quantitative {axis} log-scale evidence in layered, "
                "transformed, or unsupported mark specifications.",
                suggestion="Audit an untransformed directly encoded line, point, circle, bar, or tick view.",
                field=label,
            )
            continue

        encoding = spec["encoding"]
        if any(
            isinstance(encoding.get(channel), Mapping)
            and any(key in encoding[channel] for key in _UNSUPPORTED_TRANSFORM_KEYS)
            for channel in ("x", "y")
        ):
            report.add(
                RULE, WARN,
                f"Cannot verify quantitative {axis} log-scale source values under "
                "aggregate, bin, timeUnit, or stack semantics.",
                field=label,
            )
            continue

        values, skipped, unavailable = _find_values(
            spec, data, axis=axis, definition=definition, records=records,
        )
        if unavailable is not None:
            report.add(
                RULE, WARN, f"Cannot verify quantitative {axis} log scale: {unavailable}.",
                suggestion="Supply complete untransformed source evidence for the encoded field.",
                field=label,
            )
            continue

        zeros = sum(value == 0 for value in values)
        positive = sum(value > 0 for value in values)
        negative = sum(value < 0 for value in values)
        field_text = repr(field)
        checked = len(values)

        if zeros:
            report.add(
                RULE, FAIL,
                f"{zeros} of {checked} finite plotted {field_text} observations equal zero "
                f"on the quantitative {axis} log axis. Log(0) is undefined.",
                suggestion="Use linear/symlog scaling to represent zero; do not silently drop observations.",
                field=label,
            )
            continue

        if positive and negative:
            report.add(
                RULE, FAIL,
                f"{positive} positive and {negative} negative plotted {field_text} "
                f"observations cross zero on the quantitative {axis} log axis; "
                "a single log domain cannot represent both signs.",
                suggestion="Use linear/symlog scaling or split the explicitly disclosed populations.",
                field=label,
            )
            continue

        observed_sign = 1 if positive else -1
        if sign is not None and sign != observed_sign:
            report.add(
                RULE, FAIL,
                f"All {checked} plotted {field_text} observations are "
                f"{'positive' if observed_sign > 0 else 'negative'}, but the "
                f"quantitative {axis} log domain is "
                f"{'positive' if sign > 0 else 'negative'} only.",
                suggestion="Correct the axis domain or use a scale compatible with the source.",
                field=label,
            )
            continue

        if unknown_domain is not None:
            report.add(
                RULE, WARN,
                f"Cannot verify quantitative {axis} log-scale domain: {unknown_domain}; "
                f"{checked} checked source observations are all "
                f"{'positive' if observed_sign > 0 else 'negative'}.",
                field=label,
            )
            continue

        if skipped:
            report.add(
                RULE, WARN,
                f"All {checked} finite plotted {field_text} observations have one "
                f"valid sign for the quantitative {axis} log axis, but {skipped} "
                "invalid/null companion or metric row(s) could not be checked.",
                field=label,
            )
            continue

        report.add(
            RULE, PASS,
            f"All {checked} plotted {field_text} observations are strictly "
            f"{'positive' if observed_sign > 0 else 'negative'} and compatible "
            f"with the quantitative {axis} log domain.",
            field=label,
        )
