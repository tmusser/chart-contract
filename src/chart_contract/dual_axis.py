"""Review potentially misleading overlaid quantitative measures on independent y scales.

The check recognizes the explicit Vega-Lite dual-axis pattern:
layered marks with resolve.scale.y = "independent".
It never infers correlation, calculates scale alignment, or rejects an
intentionally designed dual-axis chart automatically.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
import json
from typing import Any

from .audit import WARN, AuditReport

RULE = "visual.dual_axis.review"
_COMPOSITIONS = ("concat", "hconcat", "vconcat")
_QUANTITATIVE = {"quantitative", "Q"}


def _encoding_with_inheritance(
    parent: Mapping[str, Any], node: Mapping[str, Any],
) -> dict[str, Any]:
    """Layered unit views inherit parent channels unless overridden."""
    merged = dict(parent)
    encoding = node.get("encoding")
    if isinstance(encoding, Mapping):
        merged.update(encoding)
    return merged


def _measure(encoding: Mapping[str, Any]) -> tuple[str, str] | None:
    y = encoding.get("y")
    if not isinstance(y, Mapping) or y.get("type") not in _QUANTITATIVE:
        return None
    field = y.get("field")
    if not isinstance(field, str) or not field.strip():
        return None

    # Same field with different aggregation is a distinct displayed measure.
    # Deterministic JSON for supported Vega-Lite scalar/dict parameters.
    identity = {
        "field": field,
        "aggregate": y.get("aggregate"),
        "timeUnit": y.get("timeUnit"),
        "bin": y.get("bin"),
    }
    try:
        signature = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return None

    label = field
    if isinstance(y.get("aggregate"), str):
        label += f" ({y['aggregate']})"
    return signature, label


def _leaf_y_measures(
    node: Mapping[str, Any],
    inherited: Mapping[str, Any],
) -> list[tuple[str, str]]:
    """Collect direct source y measures from unit marks within *one overlay*.

    Concatenated or faceted panels are not layers within a single plot, and
    must not become evidence of overlaid axes. A y2 range bound belongs to
    its unit view's y axis; it is not counted as a second axis.
    """
    effective = _encoding_with_inheritance(inherited, node)
    nested = node.get("layer")
    if isinstance(nested, list):
        result: list[tuple[str, str]] = []
        for child in nested:
            if isinstance(child, Mapping):
                result.extend(_leaf_y_measures(child, effective))
        return result

    # A unit view needs an actual mark, not just a reference or encoding object.
    mark = node.get("mark")
    mark_type = mark.get("type") if isinstance(mark, Mapping) else mark
    if not isinstance(mark_type, str) or not mark_type:
        return []
    measure = _measure(effective)
    return [measure] if measure is not None else []


def _iter_layer_groups(
    spec: Mapping[str, Any],
    path: str = "",
    inherited: Mapping[str, Any] | None = None,
) -> Iterator[tuple[str, Mapping[str, Any], Mapping[str, Any]]]:
    """Traverse nested compositions; only layer groups can create an overlay."""
    parent = inherited or {}
    effective = _encoding_with_inheritance(parent, spec)

    layers = spec.get("layer")
    if isinstance(layers, list):
        yield path, spec, parent
        for index, child in enumerate(layers):
            if isinstance(child, Mapping):
                child_path = f"{path}.layer[{index}]" if path else f"layer[{index}]"
                yield from _iter_layer_groups(child, child_path, effective)

    for key in _COMPOSITIONS:
        views = spec.get(key)
        if isinstance(views, list):
            for index, child in enumerate(views):
                if isinstance(child, Mapping):
                    child_path = f"{path}.{key}[{index}]" if path else f"{key}[{index}]"
                    # Separate panels have their own unit-view scale systems.
                    yield from _iter_layer_groups(child, child_path, {})

    sub_spec = spec.get("spec")
    if isinstance(sub_spec, Mapping):
        child_path = f"{path}.spec" if path else "spec"
        yield from _iter_layer_groups(sub_spec, child_path, {})


def audit_dual_axis(report: AuditReport, spec: Mapping[str, Any]) -> None:
    """WARN for multi-measure layered charts with independently scaled y axes."""
    for path, group, parent in _iter_layer_groups(spec):
        resolve = group.get("resolve")
        if not isinstance(resolve, Mapping):
            continue
        scales = resolve.get("scale")
        if not isinstance(scales, Mapping) or scales.get("y") != "independent":
            continue

        measures = _leaf_y_measures(group, parent)
        distinct: dict[str, str] = {}
        for signature, label in measures:
            distinct[signature] = label
        if len(distinct) < 2:
            continue

        location = f"{path}.resolve.scale.y" if path else "resolve.scale.y"
        labels = sorted(distinct.values())
        preview = ", ".join(repr(label) for label in labels[:4])
        if len(labels) > 4:
            preview += f", and {len(labels) - 4} more"

        report.add(
            RULE, WARN,
            f"Layered chart overlays {len(distinct)} distinct quantitative y measures "
            f"({preview}) using independently scaled y axes. Their apparent alignment "
            "may depend on axis ranges and does not establish correlation.",
            suggestion=(
                "Review and clearly label both axes; consider aligned small multiples "
                "or another shared-scale view if the relationship is the central claim. "
                "Retain deliberate dual axes with a documented interpretation caveat."
            ),
            field=location,
        )
