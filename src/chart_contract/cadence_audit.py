"""First-party and external Vega-Lite trend cadence audit integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from .audit import FAIL, PASS, AuditReport
from .cadence import (
    CADENCE_CONTRACT_KEY,
    build_cadence_receipt,
    cadence_outcome,
    chart_cadence_declaration,
    parse_cadence_contract,
    validate_cadence_declaration,
)


def audit_cadence_chart(report: AuditReport, chart: Any) -> None:
    declared = chart_cadence_declaration(chart)
    if declared is None:
        return
    if chart.intent != "trend":
        report.add("contract.trend.cadence", FAIL, "Cadence contract supports trend charts only.")
        return
    try:
        validated = validate_cadence_declaration(declared)
        if validated["date_field"] == getattr(chart, "y", None):
            raise ValueError("Cadence date_field must differ from the metric field.")
    except ValueError as exc:
        report.add("contract.trend.cadence", FAIL, str(exc))
        return
    report.add("contract.trend.cadence", PASS, "Closed trend cadence v1 declaration is valid.")
    try:
        receipt = build_cadence_receipt(chart.data, validated)
    except ValueError as exc:
        report.add("data.trend.cadence_evidence", FAIL, str(exc))
        return
    report.add("data.trend.cadence_evidence", PASS, "Cadence period receipts recompute from original source dates.")
    severity, message = cadence_outcome(receipt)
    report.add("data.trend.cadence", severity, message)


def _trend_visible(spec: Mapping[str, Any], encoding: Any, field: str) -> bool:
    # Only simple external line specs are in scope; no guessing layered semantics.
    mark = spec.get("mark")
    mark_type = mark.get("type") if isinstance(mark, Mapping) else mark
    if mark_type != "line" or not isinstance(encoding, Mapping):
        return False
    x = encoding.get("x")
    y = encoding.get("y")
    return (
        isinstance(x, Mapping) and x.get("field") == field
        and x.get("type") in {"temporal", "ordinal"}
        and isinstance(y, Mapping) and y.get("type") == "quantitative"
        and isinstance(y.get("field"), str) and y["field"] != field
    )


def audit_cadence_spec(
    report: AuditReport, spec: Mapping[str, Any], encoding: Any, frame: pd.DataFrame | None,
) -> None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or CADENCE_CONTRACT_KEY not in usermeta:
        return
    try:
        receipt = parse_cadence_contract(spec)
        if receipt is None:
            return
        if not _trend_visible(spec, encoding, receipt["date_field"]):
            raise ValueError(
                "Cadence requires a simple line spec with the declared date_field "
                "on visible ordinal/temporal x and a quantitative y."
            )
    except ValueError as exc:
        report.add("contract.trend.cadence", FAIL, str(exc), field="usermeta.cadence_contract")
        return
    report.add("contract.trend.cadence", PASS, "Closed cadence declaration binds the displayed trend date field.")
    if frame is None:
        report.add("data.trend.cadence_evidence", FAIL, "Cadence requires reconstructable source rows.")
        return
    try:
        current = build_cadence_receipt(
            frame, {key: receipt[key] for key in ("version", "date_field", "frequency", "require_complete")},
        )
    except ValueError as exc:
        report.add("data.trend.cadence_evidence", FAIL, str(exc))
        return
    keys = ("start_date", "end_date", "observed_count", "expected_count", "missing_count", "missing_preview")
    if any(current[key] != receipt[key] for key in keys):
        report.add("data.trend.cadence_evidence", FAIL, "Stale cadence receipts: source dates or gaps have changed.")
        return
    report.add("data.trend.cadence_evidence", PASS, "Cadence receipts match original supplied source dates.")
    severity, message = cadence_outcome(current)
    report.add("data.trend.cadence", severity, message)
