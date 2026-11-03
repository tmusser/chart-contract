"""Audit observations outside explicitly declared quantitative Vega-Lite axes.

A requested zoom is permitted by the authorization rule, but should not
silently conceal source values. This check never rewrites the scale or data.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from numbers import Real
from typing import Any

import pandas as pd

from .audit import PASS, WARN, AuditReport, _coerce_records

RULE = "visual.scale.clipped_data"
_SUPPORTED_MARKS = {"line", "point", "circle", "bar", "tick"}
_UNSUPPORTED_TRANSFORM_KEYS = {"aggregate", "bin", "timeUnit", "stack"}


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    try:
        number = float(value)
    except (ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _numeric_limits(scale: Mapping[str, Any]) -> tuple[float | None, float | None] | None:
    """Return bounds or None for dynamic/unsupported declarations.

    Only native numeric domains and domainMin/domainMax are safely checkable.
    A mixed domain/domainMin or domainMax declaration is intentionally left
    unverified rather than guessing the renderer's precedence.
    """
    if "domainRaw" in scale:
        return None
    if "domain" in scale and ("domainMin" in scale or "domainMax" in scale):
        return None
    if "domain" in scale:
        domain = scale["domain"]
        if not isinstance(domain, list) or len(domain) != 2:
            return None
        low, high = (_finite_number(item) for item in domain)
        if low is None or high is None or low >= high:
            return None
        return low, high
    low = _finite_number(scale["domainMin"]) if "domainMin" in scale else None
    high = _finite_number(scale["domainMax"]) if "domainMax" in scale else None
    if "domainMin" in scale and low is None:
        return None
    if "domainMax" in scale and high is None:
        return None
    if low is not None and high is not None and low >= high:
        return None
    return low, high


def _mark_type(view: Mapping[str, Any]) -> str:
    mark = view.get("mark")
    if isinstance(mark, str):
        return mark
    if isinstance(mark, Mapping) and isinstance(mark.get("type"), str):
        return mark["type"]
    return ""


def _nested_or_transformed(spec: Mapping[str, Any]) -> bool:
    return any(key in spec for key in (
        "layer", "concat", "hconcat", "vconcat", "spec", "transform",
    ))


def _iter_views(spec: Mapping[str, Any]):
    yield spec
    for key in ("layer", "concat", "hconcat", "vconcat"):
        children = spec.get(key)
        if isinstance(children, list):
            for child in children:
                if isinstance(child, Mapping):
                    yield from _iter_views(child)
    nested = spec.get("spec")
    if isinstance(nested, Mapping):
        yield from _iter_views(nested)


def _quantitative_bounds(view: Mapping[str, Any]):
    encoding = view.get("encoding")
    if not isinstance(encoding, Mapping):
        return
    for channel in ("x", "y"):
        definition = encoding.get(channel)
        if not isinstance(definition, Mapping) or definition.get("type") not in ("quantitative", "Q"):
            continue
        scale = definition.get("scale")
        if not isinstance(scale, Mapping):
            continue
        if any(key in scale for key in ("domain", "domainMin", "domainMax", "domainRaw")):
            yield channel, definition, scale


def _visible_pairs(
    records: Sequence[Mapping[str, Any]],
    encoding: Mapping[str, Any],
    channel: str,
    field: str,
) -> tuple[list[float], int]:
    """Inspect only rows that could contribute a visible primary mark."""
    other_channel = "x" if channel == "y" else "y"
    other = encoding.get(other_channel)
    companion_field = other.get("field") if isinstance(other, Mapping) else None
    values: list[float] = []
    skipped = 0
    for row in records:
        if not isinstance(row, Mapping):
            skipped += 1
            continue
        if companion_field:
            companion = row.get(companion_field)
            if companion is None:
                skipped += 1
                continue
            if isinstance(companion, Real) and _finite_number(companion) is None:
                skipped += 1
                continue
        raw = row.get(field)
        number = _finite_number(raw)
        if number is None:
            skipped += 1
            continue
        values.append(number)
    return values, skipped


def audit_scale_clipping(
    report: AuditReport,
    spec: Mapping[str, Any],
    data: pd.DataFrame | Sequence[Mapping[str, Any]] | None,
) -> None:
    """Warn on off-axis source observations even if scale zoom was authorized.

    The visibility assessment is intentionally conservative: transformed,
    layered, dynamic-domain or non-reconstructable plots receive a REVIEW
    warning instead of a fabricated coverage PASS.
    """
    views = list(_iter_views(spec))
    candidates = [
        (view, channel, definition, scale)
        for view in views
        for channel, definition, scale in _quantitative_bounds(view)
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
    for view, channel, definition, scale in candidates:
        label = f"encoding.{channel}.scale"
        limits = _numeric_limits(scale)
        if limits is None:
            report.add(
                RULE, WARN,
                f"Cannot verify quantitative {channel} scale coverage: domain is dynamic, "
                "malformed, or combines domain with domainMin/domainMax.",
                suggestion="Use a valid explicit numeric domain to enable source coverage verification.",
                field=label,
            )
            continue

        if not simple or view is not spec:
            report.add(
                RULE, WARN,
                f"Cannot verify quantitative {channel} scale coverage in a layered, "
                "transformed, or unsupported mark specification.",
                suggestion="Audit a simple untransformed mark with directly encoded source values.",
                field=label,
            )
            continue

        encoding = spec["encoding"]
        if any(
            isinstance(encoding.get(axis), Mapping)
            and any(key in encoding[axis] for key in _UNSUPPORTED_TRANSFORM_KEYS)
            for axis in ("x", "y")
        ):
            report.add(
                RULE, WARN,
                f"Cannot verify quantitative {channel} axis coverage because its displayed "
                "values may be computed by aggregate, bin, timeUnit, or stack semantics.",
                field=label,
            )
            continue

        field = definition.get("field")
        if not isinstance(field, str) or not field.strip():
            report.add(
                RULE, WARN,
                f"Cannot verify quantitative {channel} axis: no direct source field is encoded.",
                field=label,
            )
            continue

        if not records or not isinstance(records, list):
            report.add(
                RULE, WARN,
                f"Cannot verify quantitative {channel} axis coverage without reconstructable source rows.",
                field=label,
            )
            continue

        if any(field not in row for row in records if isinstance(row, Mapping)):
            report.add(
                RULE, WARN,
                f"Cannot verify quantitative {channel} axis coverage: source field {field!r} is missing.",
                field=label,
            )
            continue

        if not isinstance(encoding, Mapping):
            continue
        values, skipped = _visible_pairs(records, encoding, channel, field)
        if not values:
            report.add(
                RULE, WARN,
                f"Cannot verify quantitative {channel} axis coverage: no finite plotted observations.",
                field=label,
            )
            continue

        low, high = limits
        outside = [value for value in values if (low is not None and value < low)
                   or (high is not None and value > high)]
        domain_description = (
            f"[{low if low is not None else '-infinity'}, "
            f"{high if high is not None else '+infinity'}]"
        )
        if outside:
            clipping_enabled = isinstance(view.get("mark"), Mapping) and view["mark"].get("clip") is True
            report.add(
                RULE, WARN,
                f"{len(outside)} of {len(values)} plotted {field!r} observations are "
                f"outside the explicit {channel}-axis range {domain_description} "
                f"(observed range [{min(values):g}, {max(values):g}]). "
                + ("Mark clipping is enabled; these observations can be hidden."
                   if clipping_enabled else "These observations may be off-plot or clipped.")
                + (f" {skipped} invalid/null row(s) were not checked." if skipped else ""),
                suggestion="Review the requested zoom and disclose or restore omitted observations; do not silently alter the data.",
                field=label,
            )
        elif skipped:
            report.add(
                RULE, WARN,
                f"All {len(values)} finite plotted {field!r} observations are within "
                f"{domain_description}, but {skipped} invalid/null row(s) could not be checked.",
                field=label,
            )
        else:
            report.add(
                RULE, PASS,
                f"All {len(values)} plotted {field!r} observations lie within "
                f"the explicit {channel}-axis range {domain_description}.",
                field=label,
            )
