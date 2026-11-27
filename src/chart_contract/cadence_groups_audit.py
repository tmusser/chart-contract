"""Audit integration for optional declared subgroup × reporting-period grids."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from .audit import FAIL, PASS, AuditReport
from .cadence_groups import (
    GROUP_CADENCE_KEY,
    build_group_cadence_receipt,
    chart_group_cadence_declaration,
    group_cadence_outcome,
    parse_group_cadence_contract,
    validate_group_cadence_declaration,
)

_INPUT_NAMES = (
    "version", "date_field", "group_field", "frequency", "require_complete",
    "expected_groups", "expected_start", "expected_end",
)
_RECEIPT_NAMES = (
    "start_date", "end_date", "observed_count", "expected_period_count",
    "expected_cell_count", "missing_count", "missing_preview",
)


def audit_group_cadence_chart(report: AuditReport, chart: Any) -> None:
    raw = chart_group_cadence_declaration(chart)
    if raw is None:
        return
    try:
        if chart.intent != "trend":
            raise ValueError("Group cadence supports trend charts only.")
        declaration = validate_group_cadence_declaration(raw)
        if declaration["group_field"] == chart.y or declaration["date_field"] == chart.y:
            raise ValueError("Group cadence metric field must differ from date/group.")
        if any(getattr(chart, value, None) is not None for value in (
            "interval_kind", "metric_target", "event",
        )):
            raise ValueError("Group cadence v1 requires a simple unlayered grouped line.")
    except ValueError as exc:
        report.add("contract.trend.cadence_groups", FAIL, str(exc))
        return
    report.add("contract.trend.cadence_groups", PASS, "Closed grouped trend cadence v1 declaration is valid.")

    try:
        receipt = build_group_cadence_receipt(chart.data, declaration)
    except ValueError as exc:
        report.add("data.trend.cadence_groups_evidence", FAIL, str(exc))
        return
    report.add("data.trend.cadence_groups_evidence", PASS, "Group × period counts derive from original source rows.")
    severity, message = group_cadence_outcome(receipt)
    report.add("data.trend.cadence.groups", severity, message)


def _visible_group_trend(spec: Mapping[str, Any], date_field: str, group_field: str) -> bool:
    if any(key in spec for key in ("layer", "concat", "hconcat", "vconcat", "spec", "transform", "facet", "repeat")):
        return False
    mark = spec.get("mark")
    mark_type = mark.get("type") if isinstance(mark, Mapping) else mark
    encoding = spec.get("encoding")
    if mark_type != "line" or not isinstance(encoding, Mapping):
        return False
    x, y, color = (encoding.get(k) for k in ("x", "y", "color"))
    return (
        isinstance(x, Mapping) and x.get("field") == date_field
        and x.get("type") in ("temporal", "ordinal")
        and isinstance(y, Mapping) and y.get("type") in ("quantitative", "Q")
        and isinstance(y.get("field"), str) and y["field"] not in (date_field, group_field)
        and isinstance(color, Mapping) and color.get("field") == group_field
        and color.get("type") in ("nominal", "ordinal", "N", "O")
        and all(
            not isinstance(channel, Mapping) or not any(
                op in channel for op in ("aggregate", "bin", "timeUnit", "stack")
            )
            for channel in (x, y, color)
        )
    )


def audit_group_cadence_spec(
    report: AuditReport, spec: Mapping[str, Any], frame: pd.DataFrame | None,
) -> None:
    meta = spec.get("usermeta")
    if not isinstance(meta, Mapping) or GROUP_CADENCE_KEY not in meta:
        return
    try:
        receipt = parse_group_cadence_contract(spec)
        if receipt is None:
            return
        if not _visible_group_trend(spec, receipt["date_field"], receipt["group_field"]):
            raise ValueError(
                "Group cadence requires a simple untransformed line with the declared date on "
                "ordinal/temporal x, quantitative y, and the declared subgroup on nominal/ordinal color."
            )
    except ValueError as exc:
        report.add("contract.trend.cadence_groups", FAIL, str(exc), field="usermeta.group_cadence_contract")
        return
    report.add("contract.trend.cadence_groups", PASS, "Closed group cadence declaration binds visible date and color.")

    if frame is None:
        report.add("data.trend.cadence_groups_evidence", FAIL, "Group cadence requires reconstructable source rows.")
        return
    try:
        current = build_group_cadence_receipt(frame, {k: receipt[k] for k in _INPUT_NAMES})
    except ValueError as exc:
        report.add("data.trend.cadence_groups_evidence", FAIL, str(exc))
        return
    if any(current[key] != receipt[key] for key in _RECEIPT_NAMES):
        report.add("data.trend.cadence_groups_evidence", FAIL, "Stale group cadence receipts: supplied source grid changed.")
        return

    report.add("data.trend.cadence_groups_evidence", PASS, "Original source rows reproduce every group cadence receipt.")
    severity, message = group_cadence_outcome(current)
    report.add("data.trend.cadence.groups", severity, message)
