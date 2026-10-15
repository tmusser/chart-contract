"""Audit measurement-unit identity and fixed multiplicative conversions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from .audit import FAIL, PASS, AuditReport, _encoding_field, _encoding_type, _iter_encoding_definitions
from .unit_conversion import (
    UNIT_CONVERSION_INTENTS,
    chart_unit_conversion_contract,
    conversion_arithmetic_status,
    parse_unit_conversion_contract,
    source_unit_basis_status,
)


def audit_unit_conversion_chart(report: AuditReport, chart: Any) -> None:
    if getattr(chart, "intent", None) not in UNIT_CONVERSION_INTENTS:
        return
    raw = chart_unit_conversion_contract(chart)
    if raw is None:
        return
    try:
        contract = parse_unit_conversion_contract({"usermeta": {"unit_conversion_contract": raw}})
    except ValueError as exc:
        report.add("contract.unit.conversion", FAIL, str(exc).replace("usermeta.unit_conversion_contract.", "unit conversion contract "), field="source_unit")
        return
    if contract["metric_field"] != getattr(chart, "y", None):
        report.add("contract.unit.conversion", FAIL, "Unit conversion contract is not bound to the chart quantitative metric.", field="y")
        return
    report.add("contract.unit.conversion", PASS, f"Metric declares {contract['source_unit']!r} -> {contract['display_unit']!r} conversion kind {contract['conversion_kind']!r}.")
    _audit_evidence(report, chart.data, contract, "source_unit_basis_field")


def audit_unit_conversion_spec(report: AuditReport, spec: Mapping[str, Any], encoding: Any, frame: pd.DataFrame | None, unit: str | None) -> None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or "unit_conversion_contract" not in usermeta:
        return
    try:
        contract = parse_unit_conversion_contract(spec)
    except ValueError as exc:
        report.add("contract.unit.conversion", FAIL, str(exc), field="usermeta.unit_conversion_contract")
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
        report.add("contract.unit.conversion", FAIL, "Unit conversion metric_field is not an encoded quantitative field.", field="usermeta.unit_conversion_contract.metric_field")
        return
    if unit != contract["display_unit"]:
        report.add("contract.unit.conversion", FAIL, "Unit conversion display_unit does not match the spec's declared unit.", field="usermeta.unit_conversion_contract.display_unit")
        return
    report.add("contract.unit.conversion", PASS, f"Spec declares {contract['source_unit']!r} -> {contract['display_unit']!r} conversion kind {contract['conversion_kind']!r}.")
    if (contract["source_unit_basis_field"] is not None or contract["conversion_kind"] == "scale") and frame is None:
        report.add("data.unit.conversion_evidence", FAIL, "Unit conversion contract requires reconstructable source evidence.", field="usermeta.unit_conversion_contract")
        return
    if frame is not None:
        _audit_evidence(report, frame, contract, "usermeta.unit_conversion_contract.source_unit_basis_field")


def _audit_evidence(report: AuditReport, frame: pd.DataFrame, contract: Mapping[str, Any], surface_field: str) -> None:
    basis_field = contract.get("source_unit_basis_field")
    if basis_field is not None:
        ok, message = source_unit_basis_status(frame, basis_field=basis_field, source_unit=contract["source_unit"])
        report.add("data.unit.source_basis", PASS if ok else FAIL, message, field=surface_field)
    if contract["conversion_kind"] == "scale":
        ok, message = conversion_arithmetic_status(
            frame,
            metric_field=contract["metric_field"],
            source_value_field=contract["source_value_field"],
            conversion_factor=contract["conversion_factor"],
        )
        report.add("data.unit.conversion_evidence", PASS if ok else FAIL, message, field=contract["source_value_field"])
