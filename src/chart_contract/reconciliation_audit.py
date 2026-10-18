"""Audit additive component decompositions against declared control totals."""

from __future__ import annotations

import math
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
from .contracts import is_ratio_like_unit
from .reconciliation import (
    RECONCILIATION_INTENTS,
    build_reconciliation_summary,
    chart_reconciliation_declaration,
    parse_reconciliation_contract,
    reconciliation_matches,
    summaries_match,
)


def audit_reconciliation_chart(report: AuditReport, chart: Any) -> None:
    raw = chart_reconciliation_declaration(chart)
    if raw is None:
        return

    if getattr(chart, "intent", None) not in RECONCILIATION_INTENTS:
        report.add(
            "contract.reconciliation.control_total",
            FAIL,
            "Control-total reconciliation is supported only for rank/compare component decompositions in v1.",
            suggestion="Use rank/compare evidence with one explicit component field and additive metric.",
            field="control_total",
        )
        return

    contract_error = _declaration_error(raw)
    if contract_error is not None:
        report.add(
            "contract.reconciliation.control_total",
            FAIL,
            contract_error,
            suggestion=(
                "Declare one finite control_total and optional non-negative tolerance "
                "for an additive non-ratio metric."
            ),
            field="control_total",
        )
        return

    report.add(
        "contract.reconciliation.control_total",
        PASS,
        (
            f"Declared sum reconciliation binds component field {raw['component_field']!r} "
            f"and metric {raw['metric_field']!r} to control_total={float(raw['control_total']):g}."
        ),
    )

    try:
        summary = build_reconciliation_summary(chart.data, **raw)
    except ValueError as exc:
        report.add(
            "data.reconciliation.components",
            FAIL,
            str(exc),
            suggestion=(
                "Provide one complete unique component row with one finite numeric metric "
                "value per component."
            ),
            field="control_total",
        )
        return

    report.add(
        "data.reconciliation.components",
        PASS,
        (
            f"Reconciliation uses {summary.component_count} unique complete component(s) "
            f"with component_total={summary.component_total:g}."
        ),
    )
    _add_total_finding(report, summary)


def audit_reconciliation_spec(
    report: AuditReport,
    spec: Mapping[str, Any],
    encoding: Any,
    frame: pd.DataFrame | None,
    unit: str | None,
) -> None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or "reconciliation_contract" not in usermeta:
        return

    try:
        contract = parse_reconciliation_contract(spec)
    except ValueError as exc:
        report.add(
            "contract.reconciliation.control_total",
            FAIL,
            str(exc),
            suggestion="Use the exact closed version-1 reconciliation contract schema.",
            field="usermeta.reconciliation_contract",
        )
        return

    if contract is None:
        return

    if is_ratio_like_unit(unit):
        report.add(
            "contract.reconciliation.control_total",
            FAIL,
            "Control-total sum reconciliation is not supported for percent/rate/ratio metrics.",
            suggestion="Reconcile an additive numerator/count/amount instead of summing ratio-like values.",
            field="usermeta.reconciliation_contract.metric_field",
        )
        return

    visible_fields: dict[str, str | None] = {}
    for _, definition in _iter_encoding_definitions(encoding):
        field = _encoding_field(definition)
        if field:
            visible_fields[field] = _encoding_type(definition)

    if contract["component_field"] not in visible_fields:
        report.add(
            "contract.reconciliation.control_total",
            FAIL,
            (
                f"Reconciliation component field {contract['component_field']!r} is not "
                "visibly encoded in the audited spec."
            ),
            suggestion="Bind the declared component field to a visible encoding.",
            field="usermeta.reconciliation_contract.component_field",
        )
        return

    if visible_fields.get(contract["metric_field"]) != "quantitative":
        report.add(
            "contract.reconciliation.control_total",
            FAIL,
            (
                f"Reconciliation metric field {contract['metric_field']!r} is not an "
                "encoded quantitative field in the audited spec."
            ),
            suggestion="Bind reconciliation metric_field to the shown quantitative metric.",
            field="usermeta.reconciliation_contract.metric_field",
        )
        return

    report.add(
        "contract.reconciliation.control_total",
        PASS,
        (
            f"Spec declares sum reconciliation of {contract['component_field']!r} / "
            f"{contract['metric_field']!r} to control_total={contract['control_total']:g}."
        ),
    )

    if frame is None:
        report.add(
            "data.reconciliation.components",
            FAIL,
            "Reconciliation contract requires reconstructable component evidence.",
            suggestion="Provide the component rows so the control total can be recomputed.",
            field="usermeta.reconciliation_contract",
        )
        return

    try:
        actual = build_reconciliation_summary(
            frame,
            component_field=contract["component_field"],
            metric_field=contract["metric_field"],
            control_total=contract["control_total"],
            control_total_source=contract["control_total_source"],
            tolerance=contract["tolerance"],
            unit=unit,
        )
    except ValueError as exc:
        report.add(
            "data.reconciliation.components",
            FAIL,
            str(exc),
            suggestion=(
                "Provide one complete unique component row with one finite numeric metric "
                "value per component."
            ),
            field="usermeta.reconciliation_contract",
        )
        return

    report.add(
        "data.reconciliation.components",
        PASS,
        (
            f"Supplied evidence reconstructs {actual.component_count} unique component(s) "
            f"with component_total={actual.component_total:g}."
        ),
    )

    if not summaries_match(contract, actual):
        report.add(
            "data.reconciliation.total",
            FAIL,
            "Stored reconciliation receipts do not match the supplied component evidence.",
            suggestion="Regenerate reconciliation metadata from the current evidence and control total.",
            field="usermeta.reconciliation_contract",
        )
        return

    _add_total_finding(report, actual)


def _declaration_error(raw: Mapping[str, Any]) -> str | None:
    component = raw.get("component_field")
    metric = raw.get("metric_field")
    if not isinstance(component, str) or not component.strip():
        return "Reconciliation requires a non-empty component field."
    if not isinstance(metric, str) or not metric.strip():
        return "Reconciliation requires a non-empty metric field."
    if component == metric:
        return "Reconciliation component field and metric field must be distinct."
    if is_ratio_like_unit(raw.get("unit")):
        return "Control-total sum reconciliation is not supported for percent/rate/ratio metrics."

    total = raw.get("control_total")
    if isinstance(total, bool) or not isinstance(total, (int, float)):
        return "Reconciliation control_total must be a finite number."
    if not math.isfinite(float(total)):
        return "Reconciliation control_total must be a finite number."

    tolerance = raw.get("tolerance")
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)):
        return "Reconciliation tolerance must be a non-negative finite number."
    if not math.isfinite(float(tolerance)) or float(tolerance) < 0:
        return "Reconciliation tolerance must be a non-negative finite number."

    source = raw.get("control_total_source")
    if source is not None and (not isinstance(source, str) or not source.strip()):
        return "Reconciliation control_total_source must be null or a non-empty string."
    return None


def _add_total_finding(report: AuditReport, summary: Any) -> None:
    if reconciliation_matches(summary):
        report.add(
            "data.reconciliation.total",
            PASS,
            (
                f"Component total {summary.component_total:g} reconciles to control total "
                f"{summary.control_total:g} within tolerance {summary.tolerance:g}."
            ),
        )
        return

    share_text = (
        f" ({summary.represented_share * 100:.1f}% represented)"
        if summary.represented_share is not None
        else ""
    )
    report.add(
        "data.reconciliation.total",
        FAIL,
        (
            f"Component total {summary.component_total:g} does not reconcile to control total "
            f"{summary.control_total:g}; residual={summary.residual:g}{share_text}, "
            f"tolerance={summary.tolerance:g}."
        ),
        suggestion=(
            "Resolve missing/double-counted components or correct the declared control total; "
            "chart-contract will not synthesize an Unknown component."
        ),
        field="control_total",
    )
