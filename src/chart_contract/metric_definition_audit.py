"""Audit metric-definition identity and row-level version consistency."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from .audit import (
    FAIL,
    PASS,
    AuditReport,
    _encoding_field,
    _encoding_type,
    _iter_encoding_definitions,
)
from .metric_definition import (
    METRIC_DEFINITION_INTENTS,
    chart_metric_definition_contract,
    metric_basis_status,
    parse_metric_definition_contract,
)


def audit_metric_definition_chart(report: AuditReport, chart: Any) -> None:
    if getattr(chart, "intent", None) not in METRIC_DEFINITION_INTENTS:
        return

    raw_contract = chart_metric_definition_contract(chart)
    if raw_contract is None:
        return

    try:
        contract = parse_metric_definition_contract(
            {"usermeta": {"metric_definition_contract": raw_contract}}
        )
    except ValueError as exc:
        report.add(
            "contract.metric.definition",
            FAIL,
            str(exc).replace(
                "usermeta.metric_definition_contract.",
                "metric definition contract ",
            ),
            suggestion=(
                "Declare metric_id, metric_definition, and metric_version together; "
                "metric_basis_field is optional."
            ),
            field="metric_id",
        )
        return

    if contract["metric_field"] != getattr(chart, "y", None):
        report.add(
            "contract.metric.definition",
            FAIL,
            "Metric definition contract is not bound to the chart quantitative metric.",
            suggestion="Bind metric-definition identity to the chart y metric.",
            field="y",
        )
        return

    report.add(
        "contract.metric.definition",
        PASS,
        (
            f"Metric {contract['metric_id']!r} declares definition version "
            f"{contract['metric_version']!r}."
        ),
    )

    _audit_basis(
        report,
        chart.data,
        contract,
        surface_field="metric_basis_field",
    )


def audit_metric_definition_spec(
    report: AuditReport,
    spec: Mapping[str, Any],
    encoding: Any,
    frame: pd.DataFrame | None,
) -> None:
    usermeta = spec.get("usermeta")
    has_contract = (
        isinstance(usermeta, Mapping)
        and "metric_definition_contract" in usermeta
    )
    if not has_contract:
        return

    try:
        contract = parse_metric_definition_contract(spec)
    except ValueError as exc:
        report.add(
            "contract.metric.definition",
            FAIL,
            str(exc),
            suggestion="Use the exact closed version-1 metric definition contract schema.",
            field="usermeta.metric_definition_contract",
        )
        return

    if contract is None:
        return

    quantitative_fields = {
        field
        for _, definition in _iter_encoding_definitions(encoding)
        if _encoding_type(definition) == "quantitative"
        for field in [_encoding_field(definition)]
        if field
    }
    if contract["metric_field"] not in quantitative_fields:
        report.add(
            "contract.metric.definition",
            FAIL,
            (
                f"Metric definition field {contract['metric_field']!r} is not an encoded "
                "quantitative field in the audited spec."
            ),
            suggestion=(
                "Bind metric_definition_contract.metric_field to the quantitative metric "
                "shown by the spec."
            ),
            field="usermeta.metric_definition_contract.metric_field",
        )
        return

    report.add(
        "contract.metric.definition",
        PASS,
        (
            f"Metric {contract['metric_id']!r} declares definition version "
            f"{contract['metric_version']!r}."
        ),
    )

    if contract["metric_basis_field"] is not None and frame is None:
        report.add(
            "data.metric.definition_basis",
            FAIL,
            (
                "Metric definition contract declares a row-level basis field but no "
                "reconstructable evidence was supplied."
            ),
            suggestion="Provide the full evidence rows so metric-version identity can be checked.",
            field="usermeta.metric_definition_contract.metric_basis_field",
        )
        return

    if frame is not None:
        _audit_basis(
            report,
            frame,
            contract,
            surface_field="usermeta.metric_definition_contract.metric_basis_field",
        )


def _audit_basis(
    report: AuditReport,
    frame: pd.DataFrame,
    contract: Mapping[str, Any],
    *,
    surface_field: str,
) -> None:
    basis_field = contract.get("metric_basis_field")
    if basis_field is None:
        return

    ok, message = metric_basis_status(
        frame,
        basis_field=basis_field,
        metric_version=contract["metric_version"],
    )
    report.add(
        "data.metric.definition_basis",
        PASS if ok else FAIL,
        message,
        suggestion=(
            None
            if ok
            else (
                "Use one metric-definition version for the compared evidence or split "
                "definition changes into separate artifacts."
            )
        ),
        field=surface_field,
    )
