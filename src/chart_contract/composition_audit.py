"""Audit opt-in subgroup composition and Simpson-type reversals."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from .audit import FAIL, PASS, WARN, AuditReport, _encoding_field, _encoding_type, _iter_encoding_definitions
from .composition import build_composition_receipt, composition_declaration, parse_composition_contract, receipts_match


def _record(report: AuditReport, receipt: Mapping[str, Any]) -> None:
    report.add(
        "data.composition.evidence", PASS,
        f"Reconstructed {receipt['group_count']} subgroups in two matched periods; "
        f"weighted overall rate {receipt['baseline_overall']:.6g} -> "
        f"{receipt['target_overall']:.6g}.",
    )
    reversal = receipt["reversal"]
    report.add(
        "data.composition.reversal", WARN if reversal else PASS,
        (
            f"Simpson-type composition reversal: all subgroups move "
            f"{receipt['subgroup_direction']} while the weighted aggregate moves "
            f"{receipt['aggregate_direction']}; inspect population mix."
            if reversal else
            f"No unanimous subgroup-versus-aggregate direction reversal detected "
            f"(subgroups: {receipt['subgroup_direction']}; aggregate: {receipt['aggregate_direction']})."
        ),
        suggestion=(
            "Report the subgroup and weighted aggregate movements separately; "
            "review changing group weights before interpreting the overall trend."
            if reversal else None
        ),
    )


def audit_composition_chart(report: AuditReport, chart: Any) -> None:
    declaration = composition_declaration(chart)
    if declaration is None:
        return
    if chart.intent != "compare":
        report.add("contract.composition.declared", FAIL, "Composition v1 supports grouped compare charts only.")
        return
    try:
        # Verify metadata syntax even when row evidence is malformed.
        from .composition import _inputs
        _inputs(declaration)
    except ValueError as exc:
        report.add("contract.composition.declared", FAIL, str(exc))
        return
    if chart.group != declaration["group_field"] or chart.x != declaration["period_field"]:
        report.add("contract.composition.declared", FAIL, "Composition must bind visible period and subgroup fields.")
        return
    report.add("contract.composition.declared", PASS, "Closed v1 composition declaration binds period, subgroup, displayed ratio, and counts.")
    try:
        receipt = build_composition_receipt(chart.data, declaration)
    except ValueError as exc:
        report.add("data.composition.evidence", FAIL, str(exc))
        return
    _record(report, receipt)


def audit_composition_spec(
    report: AuditReport, spec: Mapping[str, Any], encoding: Any,
    frame: pd.DataFrame | None,
) -> None:
    if not isinstance(spec.get("usermeta"), Mapping) or "composition_contract" not in spec["usermeta"]:
        return
    try:
        contract = parse_composition_contract(spec)
    except ValueError as exc:
        report.add("contract.composition.declared", FAIL, str(exc))
        return
    if not isinstance(encoding, Mapping):
        report.add("contract.composition.declared", FAIL, "Composition requires visible chart encodings.")
        return
    # Tooltip-only references are not visible subgroup encodings.
    period_fields = {
        _encoding_field(encoding[name]) for name in ("x", "row", "column")
        if name in encoding
    }
    group_fields = {
        _encoding_field(encoding[name]) for name in ("color", "xOffset", "row", "column")
        if name in encoding
    }
    quantitative_fields = {
        _encoding_field(value) for name, value in _iter_encoding_definitions(encoding)
        if name in ("x", "y") and _encoding_type(value) == "quantitative"
    }
    if (contract["period_field"] not in period_fields
        or contract["group_field"] not in group_fields
        or contract["metric_field"] not in quantitative_fields):
        report.add(
            "contract.composition.declared", FAIL,
            "Composition period, subgroup, and metric must be visibly encoded; tooltip-only fields do not count.",
        )
        return
    report.add("contract.composition.declared", PASS, "Closed composition metadata is visibly bound to the chart.")
    if frame is None:
        report.add("data.composition.evidence", FAIL, "Composition contract requires reconstructable source evidence.")
        return
    try:
        expected = build_composition_receipt(
            frame, {key: contract[key] for key in (
                "version", "period_field", "group_field", "metric_field",
                "numerator_field", "denominator_field", "baseline_value",
                "target_value", "multiplier", "tolerance",
            )}
        )
    except ValueError as exc:
        report.add("data.composition.evidence", FAIL, str(exc))
        return
    if not receipts_match(contract, expected):
        report.add("data.composition.evidence", FAIL, "Stored composition receipts disagree with recomputed source evidence.")
        return
    _record(report, expected)
