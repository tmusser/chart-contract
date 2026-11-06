"""Explicit cross-chart additive reconciliation of displayed source evidence.

No source-side totals, transforms, or chart claims are trusted as a control:
the headline's one observed metric value is the comparison total.
"""

from __future__ import annotations

from collections.abc import Mapping
import math
from numbers import Real
from typing import Any

import pandas as pd

from .audit import FAIL, PASS, WARN, AuditFinding, _coerce_records
from .contracts import declared_unit_from_spec, declared_value_representation_from_spec, is_ratio_like_unit
from .reconciliation import build_reconciliation_summary

RECONCILIATION_KIND = "sum_reconciliation"
SUM_FIELDS = frozenset({
    "kind", "id", "total_artifact_id", "components_artifact_id",
    "total_metric_field", "component_field", "component_metric_field",
    "components_exhaustive", "tolerance",
})


def parse_sum_relationship(raw: Mapping[str, Any], artifact_ids: set[str]) -> dict[str, Any]:
    """A closed v1 relationship with a distinct headline and breakdown."""
    if not isinstance(raw, Mapping) or set(raw) != SUM_FIELDS:
        raise ValueError("Bundle sum_reconciliation relationship requires the exact closed field set.")
    if raw["kind"] != RECONCILIATION_KIND:
        raise ValueError("Unsupported bundle reconciliation kind.")
    parsed: dict[str, Any] = {"kind": RECONCILIATION_KIND}
    for field in (
        "id", "total_artifact_id", "components_artifact_id",
        "total_metric_field", "component_field", "component_metric_field",
    ):
        value = raw[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Bundle reconciliation {field} must be a non-empty string.")
        parsed[field] = value
    total_id = parsed["total_artifact_id"]
    components_id = parsed["components_artifact_id"]
    if total_id == components_id or not {total_id, components_id} <= artifact_ids:
        raise ValueError("Bundle reconciliation needs two distinct declared artifact IDs.")
    if parsed["component_field"] == parsed["component_metric_field"]:
        raise ValueError("Bundle reconciliation component and metric fields must be distinct.")
    if type(raw["components_exhaustive"]) is not bool or not raw["components_exhaustive"]:
        raise ValueError("Bundle reconciliation requires components_exhaustive=true.")
    tolerance = raw["tolerance"]
    if isinstance(tolerance, bool) or not isinstance(tolerance, Real):
        raise ValueError("Bundle reconciliation tolerance must be a finite non-negative number.")
    try:
        parsed_tolerance = float(tolerance)
    except (ValueError, OverflowError) as exc:
        raise ValueError("Bundle reconciliation tolerance must be finite.") from exc
    if not math.isfinite(parsed_tolerance) or parsed_tolerance < 0:
        raise ValueError("Bundle reconciliation tolerance must be a finite non-negative number.")
    parsed["components_exhaustive"] = True
    parsed["tolerance"] = parsed_tolerance
    return parsed


def _plain(spec: Mapping[str, Any], *, kind: str) -> Mapping[str, Any]:
    """Only an untransformed single-view bar/point mark is reconstructable."""
    if any(key in spec for key in (
        "transform", "layer", "concat", "hconcat", "vconcat", "spec",
        "facet", "repeat",
    )):
        raise ValueError(f"{kind} must be a single-view untransformed bar or point chart.")
    mark = spec.get("mark")
    mark_type = mark.get("type") if isinstance(mark, Mapping) else mark
    if mark_type not in ("bar", "point"):
        raise ValueError(f"{kind} must use a directly encoded bar or point mark.")
    encoding = spec.get("encoding")
    if not isinstance(encoding, Mapping) or not set(encoding) <= {"x", "y", "tooltip"}:
        raise ValueError(f"{kind} must use direct x/y encodings without grouping or color stacks.")
    for axis in ("x", "y"):
        definition = encoding.get(axis)
        if definition is not None and (
            not isinstance(definition, Mapping)
            or any(k in definition for k in ("aggregate", "bin", "timeUnit", "stack"))
        ):
            raise ValueError(f"{kind} may not aggregate, bin, stack, or transform its encoded evidence.")
    return encoding


def _metric(spec: Mapping[str, Any], expected_field: str, *, kind: str) -> None:
    encoding = _plain(spec, kind=kind)
    y = encoding.get("y")
    if not isinstance(y, Mapping) or y.get("field") != expected_field or y.get("type") not in ("quantitative", "Q"):
        raise ValueError(
            f"{kind} must display metric {expected_field!r} as a direct quantitative y field."
        )


def _frame(spec: Mapping[str, Any], data: pd.DataFrame | None, *, kind: str) -> pd.DataFrame:
    records = _coerce_records(spec, data)
    if records is None:
        raise ValueError(f"{kind} requires reconstructable source rows.")
    frame = pd.DataFrame(records)
    if frame.empty:
        raise ValueError(f"{kind} requires at least one source row.")
    return frame


def _headline_total(frame: pd.DataFrame, field: str) -> float:
    if len(frame) != 1 or field not in frame.columns:
        raise ValueError("Headline total must resolve to exactly one source row and displayed metric field.")
    raw = frame[field].iloc[0]
    if isinstance(raw, bool) or not isinstance(raw, Real):
        raise ValueError("Headline metric value must be finite numeric, not a boolean or label.")
    try:
        total = float(raw)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Headline metric value must be finite numeric.") from exc
    if not math.isfinite(total):
        raise ValueError("Headline metric value must be finite numeric.")
    return total


def audit_sum_relationship(
    relation: Mapping[str, Any],
    specs: Mapping[str, Mapping[str, Any]],
    data: Mapping[str, pd.DataFrame | None],
    reports: Mapping[str, Any],
) -> list[AuditFinding]:
    rid = relation["id"]
    headline_id = relation["total_artifact_id"]
    breakdown_id = relation["components_artifact_id"]
    if any(reports[key].verdict == "BLOCK" for key in (headline_id, breakdown_id)):
        return [AuditFinding(
            "bundle.reconciliation.skipped", WARN,
            f"Relationship {rid!r} reconciliation skipped: at least one component artifact is BLOCK.",
        )]

    try:
        headline_spec, breakdown_spec = specs[headline_id], specs[breakdown_id]
        headline_unit = declared_unit_from_spec(headline_spec)
        breakdown_unit = declared_unit_from_spec(breakdown_spec)
        if (not isinstance(headline_unit, str) or not headline_unit.strip()
                or not isinstance(breakdown_unit, str) or not breakdown_unit.strip()):
            raise ValueError("Both charts must declare a non-empty additive measurement unit.")
        if (headline_unit != breakdown_unit
                or declared_value_representation_from_spec(headline_spec)
                != declared_value_representation_from_spec(breakdown_spec)):
            raise ValueError("Headline and breakdown must have matching declared units and representations.")
        if is_ratio_like_unit(headline_unit):
            raise ValueError("Sum reconciliation does not support percent, rate, or ratio metrics.")

        _metric(headline_spec, relation["total_metric_field"], kind="Headline")
        _metric(breakdown_spec, relation["component_metric_field"], kind="Breakdown")
        encoding = _plain(breakdown_spec, kind="Breakdown")
        component = encoding.get("x")
        if not isinstance(component, Mapping) or (
            component.get("field") != relation["component_field"]
            or component.get("type") not in ("nominal", "ordinal", "N", "O")
        ):
            raise ValueError("Breakdown must visibly encode distinct component labels on nominal/ordinal x.")

        headline = _frame(headline_spec, data[headline_id], kind="Headline")
        breakdown = _frame(breakdown_spec, data[breakdown_id], kind="Breakdown")
        total = _headline_total(headline, relation["total_metric_field"])
        summary = build_reconciliation_summary(
            breakdown,
            component_field=relation["component_field"],
            metric_field=relation["component_metric_field"],
            control_total=total,
            control_total_source=f"bundle:{headline_id}",
            tolerance=relation["tolerance"],
            unit=headline_unit,
        )
        if not math.isfinite(summary.component_total) or not math.isfinite(summary.residual):
            raise ValueError("Component sum and residual must be finite.")
    except (ValueError, TypeError, OverflowError) as exc:
        return [AuditFinding(
            "bundle.reconciliation.evidence", FAIL,
            f"Relationship {rid!r} has invalid or unreconstructable additive evidence: {exc}",
            suggestion="Supply one visible finite headline value and unique, complete additive component rows with matching units.",
        )]

    evidence = AuditFinding(
        "bundle.reconciliation.evidence", PASS,
        f"Relationship {rid!r} independently reconstructed headline={total:g} "
        f"and {summary.component_count} unique additive components in {headline_unit}.",
    )
    if abs(summary.residual) <= relation["tolerance"]:
        value = AuditFinding(
            "bundle.reconciliation.total", PASS,
            f"Relationship {rid!r} component sum {summary.component_total:g} "
            f"matches headline {total:g} within absolute tolerance {relation['tolerance']:g}.",
        )
    else:
        share = (
            f", represented_share={100 * summary.represented_share:.1f}%"
            if summary.represented_share is not None else ""
        )
        value = AuditFinding(
            "bundle.reconciliation.total", FAIL,
            f"Relationship {rid!r} component sum {summary.component_total:g} "
            f"does not match headline {total:g}; residual={summary.residual:g}"
            f"{share}, tolerance={relation['tolerance']:g}.",
            suggestion="Reconcile missing or double-counted breakdown components against the headline; do not synthesize an Unknown category.",
        )
    return [evidence, value]
