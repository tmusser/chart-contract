"""Audit baseline and change semantics for explicit comparisons."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from .audit import FAIL, PASS, WARN, AuditReport, _encoding_field, _encoding_type, _iter_encoding_definitions
from .comparison import (
    COMPARISON_CONTRACT_KEY,
    COMPARISON_INTENTS,
    build_comparison_summary,
    changes_match,
    comparison_declaration,
    explicit_claim_change,
    parse_comparison_contract,
)


def audit_comparison_chart(report: AuditReport, chart: Any) -> None:
    if getattr(chart, "intent", None) not in COMPARISON_INTENTS:
        return

    declaration = comparison_declaration(chart)
    claim_change = explicit_claim_change(
        getattr(chart, "claim", None),
        unit=getattr(chart, "unit", None),
    )
    if declaration is None:
        if claim_change is not None:
            report.add(
                "contract.comparison.baseline",
                WARN,
                "Claim states an explicit numeric comparison but no baseline contract is declared.",
                suggestion="Declare baseline_field, baseline_value, target_value, change_type, and declared_change.",
                field="baseline_field",
            )
        return

    if getattr(chart, "baseline_field", None) not in {getattr(chart, "x", None), getattr(chart, "group", None)}:
        report.add(
            "contract.comparison.baseline",
            FAIL,
            "Baseline field must be a visible comparison dimension (x or group) in v1.",
            field="baseline_field",
        )
        return

    try:
        summary = build_comparison_summary(
            chart.data,
            **declaration,
            unit=getattr(chart, "unit", None),
            value_representation=getattr(chart, "value_representation", None),
        )
    except ValueError as exc:
        report.add(
            "data.comparison.baseline",
            FAIL,
            str(exc),
            suggestion="Use one visible selector field with exactly one baseline row and one target row.",
            field="baseline_field",
        )
        return

    report.add(
        "contract.comparison.baseline",
        PASS,
        (
            f"Comparison baseline is explicit: {summary.baseline_field}="
            f"{summary.baseline_value!r} -> {summary.target_value!r}."
        ),
    )
    report.add(
        "data.comparison.baseline",
        PASS,
        (
            f"Baseline/target metric values resolve uniquely to "
            f"{summary.baseline_metric_value:g} and {summary.target_metric_value:g}."
        ),
    )
    if changes_match(summary.declared_change, summary.computed_change):
        report.add(
            "contract.comparison.change",
            PASS,
            (
                f"Declared {summary.change_type} change {summary.declared_change:g} "
                f"matches recomputed value {summary.computed_change:g}."
            ),
        )
    else:
        report.add(
            "contract.comparison.change",
            FAIL,
            (
                f"Declared {summary.change_type} change {summary.declared_change:g} does not "
                f"match recomputed value {summary.computed_change:g}."
            ),
            suggestion="Correct the declared change or the baseline/target selectors; do not relabel the arithmetic.",
            field="declared_change",
        )

    _audit_claim_change(report, claim_change, summary.change_type, summary.declared_change)


def audit_comparison_spec(
    report: AuditReport,
    spec: Mapping[str, Any],
    encoding: Any,
    frame: pd.DataFrame | None,
    claim: str | None,
    unit: str | None,
    value_representation: str | None,
) -> None:
    usermeta = spec.get("usermeta")
    has_contract = isinstance(usermeta, Mapping) and COMPARISON_CONTRACT_KEY in usermeta
    claim_change = explicit_claim_change(claim, unit=unit)

    if not has_contract:
        if claim_change is not None:
            report.add(
                "contract.comparison.baseline",
                WARN,
                "Claim states an explicit numeric comparison but the spec has no comparison_contract.",
                suggestion="Add an explicit baseline selector and change semantics to usermeta.comparison_contract.",
                field="usermeta.comparison_contract",
            )
        return

    try:
        contract = parse_comparison_contract(spec)
    except ValueError as exc:
        report.add(
            "contract.comparison.baseline",
            FAIL,
            str(exc),
            suggestion="Use the exact closed version-1 comparison contract schema.",
            field="usermeta.comparison_contract",
        )
        return
    if contract is None:
        return

    encoded_fields = {
        field
        for _, definition in _iter_encoding_definitions(encoding)
        for field in [_encoding_field(definition)]
        if field
    }
    quantitative_fields = {
        field
        for _, definition in _iter_encoding_definitions(encoding)
        if _encoding_type(definition) == "quantitative"
        for field in [_encoding_field(definition)]
        if field
    }
    if contract["metric_field"] not in quantitative_fields:
        report.add(
            "contract.comparison.baseline",
            FAIL,
            "comparison_contract.metric_field is not a shown quantitative field.",
            field="usermeta.comparison_contract.metric_field",
        )
        return
    if contract["baseline_field"] not in encoded_fields:
        report.add(
            "contract.comparison.baseline",
            FAIL,
            "comparison_contract.baseline_field is not a visible encoded comparison dimension.",
            field="usermeta.comparison_contract.baseline_field",
        )
        return
    if frame is None:
        report.add(
            "data.comparison.baseline",
            FAIL,
            "Comparison contract cannot be verified without reconstructable evidence.",
            suggestion="Supply the evidence rows used for the comparison.",
            field="usermeta.comparison_contract",
        )
        return

    try:
        expected = build_comparison_summary(
            frame,
            metric_field=contract["metric_field"],
            baseline_field=contract["baseline_field"],
            baseline_value=contract["baseline_value"],
            target_value=contract["target_value"],
            change_type=contract["change_type"],
            declared_change=contract["declared_change"],
            unit=unit,
            value_representation=value_representation,
        ).to_dict()
    except ValueError as exc:
        report.add(
            "data.comparison.baseline",
            FAIL,
            str(exc),
            suggestion="Provide exactly one baseline and target observation with valid change semantics.",
            field="usermeta.comparison_contract",
        )
        return

    report.add(
        "contract.comparison.baseline",
        PASS,
        "Comparison spec declares a visible baseline and target selector.",
    )
    report.add(
        "data.comparison.baseline",
        PASS,
        "Baseline and target observations resolve uniquely from supplied evidence.",
    )

    receipt_fields = ("baseline_metric_value", "target_metric_value", "computed_change")
    drift = [field for field in receipt_fields if not changes_match(float(contract[field]), float(expected[field]))]
    declared_matches = changes_match(contract["declared_change"], expected["computed_change"])
    if drift or not declared_matches:
        details = []
        if drift:
            details.append("stale receipt fields: " + ", ".join(drift))
        if not declared_matches:
            details.append(
                f"declared change {contract['declared_change']:g} != recomputed {expected['computed_change']:g}"
            )
        report.add(
            "contract.comparison.change",
            FAIL,
            "Comparison arithmetic does not match supplied evidence (" + "; ".join(details) + ").",
            suggestion="Regenerate comparison_contract from the final evidence and selectors.",
            field="usermeta.comparison_contract",
        )
    else:
        report.add(
            "contract.comparison.change",
            PASS,
            (
                f"Declared {contract['change_type']} change {contract['declared_change']:g} "
                "matches supplied evidence and stored receipts."
            ),
        )

    _audit_claim_change(report, claim_change, contract["change_type"], contract["declared_change"])


def _audit_claim_change(
    report: AuditReport,
    claim_change: tuple[str, float] | None,
    change_type: str,
    declared_change: float,
) -> None:
    if claim_change is None:
        report.add(
            "claim.comparison.change_semantics",
            PASS,
            "Claim contains no narrow explicit numeric change phrase that contradicts the comparison contract.",
        )
        return
    claim_type, claim_value = claim_change
    if claim_type != change_type:
        report.add(
            "claim.comparison.change_semantics",
            FAIL,
            (
                f"Claim expresses {claim_type} semantics ({claim_value:g}) but the "
                f"comparison contract declares {change_type}."
            ),
            suggestion="Use percentage points, percent change, ratio, or absolute delta consistently.",
            field="claim",
        )
        return
    if not changes_match(claim_value, declared_change):
        report.add(
            "claim.comparison.change_semantics",
            FAIL,
            (
                f"Claim states {claim_value:g} for {claim_type}, but comparison_contract "
                f"declares {declared_change:g}."
            ),
            suggestion="Make the claim's explicit change value match the audited comparison contract.",
            field="claim",
        )
        return
    report.add(
        "claim.comparison.change_semantics",
        PASS,
        "Claim's explicit numeric change semantics match the comparison contract.",
    )
