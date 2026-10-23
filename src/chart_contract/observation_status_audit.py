"""Audit explicit observation-state semantics against original supplied evidence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from .audit import FAIL, PASS, AuditReport, _encoding_field, _encoding_type, _iter_encoding_definitions
from .observation_status import (
    OBSERVATION_STATUS_INTENTS,
    OBSERVATION_STATUS_KEY,
    build_observation_contract,
    chart_observation_declaration,
    observation_evidence_status,
    parse_observation_contract,
)


def audit_observation_chart(report: AuditReport, chart: Any) -> None:
    if getattr(chart, "intent", None) not in OBSERVATION_STATUS_INTENTS:
        return
    declaration = chart_observation_declaration(chart)
    if declaration is None:
        return
    try:
        if not isinstance(declaration["status_field"], str) or not declaration["status_field"].strip():
            raise ValueError("Observation status field must be a non-empty string.")
        if declaration["metric_field"] == declaration["status_field"]:
            raise ValueError("Observation status field must differ from the metric field.")
    except ValueError as exc:
        report.add("contract.observation.status", FAIL, str(exc), field="observation_status_field")
        return

    report.add("contract.observation.status", PASS, "Observation status is explicitly bound to the chart metric.")
    ok, message, _ = observation_evidence_status(
        chart.data,
        metric_field=declaration["metric_field"],
        status_field=declaration["status_field"],
    )
    report.add(
        "data.observation.values", PASS if ok else FAIL, message,
        suggestion=None if ok else "Keep missing/suppressed values null and structural zeros exactly zero; never auto-impute.",
        field="observation_status_field",
    )


def audit_observation_spec(
    report: AuditReport,
    spec: Mapping[str, Any],
    encoding: Any,
    frame: pd.DataFrame | None,
) -> None:
    meta = spec.get("usermeta")
    if not isinstance(meta, Mapping) or OBSERVATION_STATUS_KEY not in meta:
        return
    try:
        contract = parse_observation_contract(spec)
    except ValueError as exc:
        report.add(
            "contract.observation.status", FAIL, str(exc),
            suggestion="Use exact version-1 metric/status fields and four state counts.",
            field="usermeta.observation_status_contract",
        )
        return
    if contract is None:
        return
    numeric_fields = {
        field
        for _, definition in _iter_encoding_definitions(encoding)
        if _encoding_type(definition) == "quantitative"
        for field in [_encoding_field(definition)]
        if field
    }
    if contract["metric_field"] not in numeric_fields:
        report.add(
            "contract.observation.status", FAIL,
            f"Observation metric field {contract['metric_field']!r} is not a displayed quantitative field.",
            field="usermeta.observation_status_contract.metric_field",
        )
        return
    report.add(
        "contract.observation.status", PASS,
        "Observation status is bound to a displayed quantitative metric.",
    )
    if frame is None:
        report.add(
            "data.observation.values", FAIL,
            "Observation status requires reconstructable source evidence; none was supplied.",
            field="usermeta.observation_status_contract",
        )
        return
    ok, message, counts = observation_evidence_status(
        frame,
        metric_field=contract["metric_field"],
        status_field=contract["status_field"],
    )
    report.add(
        "data.observation.values", PASS if ok else FAIL, message,
        field="usermeta.observation_status_contract.status_field",
    )
    if not ok:
        return
    matches = counts == contract["counts"]
    report.add(
        "data.observation.receipts", PASS if matches else FAIL,
        (
            "Observation state counts reproduce from the supplied rows."
            if matches else
            f"Observation counts are stale: contract={contract['counts']}, evidence={counts}."
        ),
        field="usermeta.observation_status_contract.counts",
    )
