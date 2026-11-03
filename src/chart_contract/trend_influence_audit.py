"""Audit declared trend influence against full and leave-one-out OLS slopes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from .audit import FAIL, PASS, AuditReport
from .trend_influence import (
    CONTRACT_KEY, INPUT_FIELDS, RECEIPT_FIELDS,
    build_influence_receipt,
    chart_influence_declaration,
    influence_outcome,
    parse_influence_contract,
    validate_declaration,
)


def audit_influence_chart(report: AuditReport, chart: Any) -> None:
    try:
        declaration = chart_influence_declaration(chart)
        if declaration is None:
            return
        if getattr(chart, "intent", None) != "trend":
            raise ValueError("Trend influence is supported on trend charts only.")
        declaration = validate_declaration(declaration)
    except ValueError as exc:
        report.add("contract.trend.influence", FAIL, str(exc))
        return
    report.add("contract.trend.influence", PASS, "Closed v1 trend influence declaration binds x and y.")
    try:
        receipt = build_influence_receipt(chart.data, declaration)
    except (ValueError, OverflowError) as exc:
        report.add("data.trend.influence_evidence", FAIL, str(exc))
        return
    report.add(
        "data.trend.influence_evidence", PASS,
        f"Recomputed full and leave-one-out OLS slopes for {receipt['row_count']} original rows.",
    )
    severity, message = influence_outcome(receipt)
    report.add("stat.trend.influence", severity, message)


def _visible_line(analytical_spec: Mapping[str, Any], encoding: Any, declaration: Mapping[str, Any]) -> bool:
    mark = analytical_spec.get("mark")
    mark_type = mark.get("type") if isinstance(mark, Mapping) else mark
    if mark_type != "line" or not isinstance(encoding, Mapping):
        return False
    x = encoding.get("x")
    y = encoding.get("y")
    if not isinstance(x, Mapping) or not isinstance(y, Mapping):
        return False
    if (x.get("field") != declaration["x_field"]
            or y.get("field") != declaration["y_field"]
            or x.get("type") not in ("quantitative", "temporal", "ordinal")
            or y.get("type") != "quantitative"):
        return False
    # Source values must be plotted directly; Vega-Lite aggregates/transforms
    # would invalidate leave-one-out calculations against supplied source rows.
    return not any(
        key in definition for definition in (x, y)
        for key in ("aggregate", "bin", "timeUnit")
    )


def audit_influence_spec(
    report: AuditReport,
    spec: Mapping[str, Any],
    analytical_spec: Mapping[str, Any],
    encoding: Any,
    frame: pd.DataFrame | None,
) -> None:
    meta = spec.get("usermeta")
    if not isinstance(meta, Mapping) or CONTRACT_KEY not in meta:
        return
    try:
        contract = parse_influence_contract(spec)
        if contract is None:
            return
        if not _visible_line(analytical_spec, encoding, contract):
            raise ValueError("Trend influence contract must bind a visible, unaggregated line x/y metric pair.")
        if spec.get("transform") or analytical_spec.get("transform"):
            raise ValueError("Trend influence does not support transformed Vega-Lite evidence.")
    except ValueError as exc:
        report.add("contract.trend.influence", FAIL, str(exc), field="usermeta.trend_influence_contract")
        return
    report.add("contract.trend.influence", PASS, "Closed v1 contract is bound to the visible untransformed trend.")
    if frame is None:
        report.add("data.trend.influence_evidence", FAIL, "Trend influence requires reconstructable original evidence.")
        return
    try:
        current = build_influence_receipt(frame, {key: contract[key] for key in INPUT_FIELDS})
    except (ValueError, OverflowError) as exc:
        report.add("data.trend.influence_evidence", FAIL, str(exc))
        return
    if any(current[key] != contract[key] for key in RECEIPT_FIELDS):
        report.add(
            "data.trend.influence_evidence", FAIL,
            "Stale trend influence receipts: full-data or leave-one-out slopes "
            "no longer reproduce from the supplied source rows.",
        )
        return
    report.add("data.trend.influence_evidence", PASS, "Trend influence receipts independently reproduce from supplied rows.")
    severity, message = influence_outcome(current)
    report.add("stat.trend.influence", severity, message)
