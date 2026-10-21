"""Audit explicit metric target/threshold semantics."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from .audit import FAIL, PASS, WARN, AuditReport, _encoding_field, _encoding_type, _iter_encoding_definitions
from .target import (
    TARGET_CONTRACT_KEY,
    TARGET_INTENTS,
    build_target_summary,
    explicit_target_claim,
    parse_target_contract,
    spec_has_target_rule,
    target_declaration,
    target_receipts_match,
)


def audit_target_chart(report: AuditReport, chart: Any) -> None:
    if getattr(chart, "intent", None) not in TARGET_INTENTS:
        return

    claim_semantics = explicit_target_claim(getattr(chart, "claim", None))
    declaration = target_declaration(chart)
    if declaration is None:
        if claim_semantics is not None:
            report.add(
                "claim.metric.target_semantics",
                WARN,
                "Claim explicitly says the target was met/missed but no metric target contract is declared.",
                suggestion=(
                    "Declare target_selector_field, target_selector_value, metric_target, "
                    "target_operator, and optional target_tolerance."
                ),
                field="metric_target",
            )
        return

    try:
        summary = build_target_summary(chart.data, **declaration)
    except ValueError as exc:
        report.add(
            "contract.metric.target",
            FAIL,
            str(exc).replace("usermeta.target_contract.", "target contract "),
            suggestion=(
                "Declare one finite scalar target, one supported operator, and one selector "
                "that resolves to exactly one observed metric value."
            ),
            field="metric_target",
        )
        return

    if summary.metric_field != getattr(chart, "y", None):
        report.add(
            "contract.metric.target",
            FAIL,
            "Target contract is not bound to the chart quantitative metric.",
            field="y",
        )
        return

    report.add(
        "contract.metric.target",
        PASS,
        (
            f"Metric {summary.metric_field!r} declares target "
            f"{summary.operator} {summary.target_value:g} with tolerance "
            f"{summary.tolerance:g}."
        ),
    )
    report.add(
        "data.metric.target_observation",
        PASS,
        (
            f"Target selector {summary.selector_field}={summary.selector_value!r} "
            f"resolves to observed value {summary.observed_value:g}; "
            f"target_met={summary.target_met}."
        ),
    )
    _add_claim_finding(report, claim_semantics, summary.target_met, field="claim")


def audit_target_spec(
    report: AuditReport,
    spec: Mapping[str, Any],
    encoding: Any,
    frame: pd.DataFrame | None,
    claim: str | None,
) -> None:
    usermeta = spec.get("usermeta")
    has_contract = isinstance(usermeta, Mapping) and TARGET_CONTRACT_KEY in usermeta
    claim_semantics = explicit_target_claim(claim)

    if not has_contract:
        if claim_semantics is not None:
            report.add(
                "claim.metric.target_semantics",
                WARN,
                "Claim explicitly says the target was met/missed but the spec has no target_contract.",
                suggestion="Add a closed usermeta.target_contract with one selected observation.",
                field="usermeta.target_contract",
            )
        return

    try:
        contract = parse_target_contract(spec)
    except ValueError as exc:
        report.add(
            "contract.metric.target",
            FAIL,
            str(exc),
            suggestion="Use the exact closed version-1 target contract schema.",
            field="usermeta.target_contract",
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
            "contract.metric.target",
            FAIL,
            "target_contract.metric_field is not a shown quantitative field.",
            field="usermeta.target_contract.metric_field",
        )
        return

    report.add(
        "contract.metric.target",
        PASS,
        (
            f"Metric {contract['metric_field']!r} declares target "
            f"{contract['operator']} {contract['target_value']:g} with tolerance "
            f"{contract['tolerance']:g}."
        ),
    )

    if frame is None:
        report.add(
            "data.metric.target_observation",
            FAIL,
            "Target contract requires reconstructable selected-observation evidence.",
            suggestion="Provide the data used by the target-bearing spec.",
            field="usermeta.target_contract",
        )
    else:
        try:
            summary = build_target_summary(
                frame,
                metric_field=contract["metric_field"],
                selector_field=contract["selector_field"],
                selector_value=contract["selector_value"],
                target_value=contract["target_value"],
                operator=contract["operator"],
                tolerance=contract["tolerance"],
            )
        except ValueError as exc:
            report.add(
                "data.metric.target_observation",
                FAIL,
                str(exc),
                suggestion="Provide exactly one finite selected target observation.",
                field="usermeta.target_contract",
            )
        else:
            if target_receipts_match(contract, summary):
                report.add(
                    "data.metric.target_observation",
                    PASS,
                    (
                        f"Selected observation recomputes to {summary.observed_value:g}; "
                        f"target_met={summary.target_met} and stored receipts match."
                    ),
                )
            else:
                report.add(
                    "data.metric.target_observation",
                    FAIL,
                    "Stored target observed-value/gap/status receipts do not match supplied evidence.",
                    suggestion="Regenerate target metadata from the current evidence.",
                    field="usermeta.target_contract",
                )

    if spec_has_target_rule(spec, contract["target_value"]):
        report.add(
            "visual.metric.target",
            PASS,
            "Spec visibly encodes the declared scalar target as a rule.",
        )
    else:
        report.add(
            "visual.metric.target",
            FAIL,
            "Spec declares target metadata but does not visibly encode the declared scalar target.",
            suggestion="Add a rule at the declared target value.",
            field="usermeta.target_contract",
        )

    _add_claim_finding(
        report,
        claim_semantics,
        contract["target_met"],
        field="claim",
    )


def _add_claim_finding(
    report: AuditReport,
    claim_semantics: str | None,
    target_met: bool,
    *,
    field: str,
) -> None:
    if claim_semantics is None:
        return
    if claim_semantics == "ambiguous":
        report.add(
            "claim.metric.target_semantics",
            FAIL,
            "Claim mixes met-target and missed-target wording.",
            suggestion="Use one unambiguous target-status statement.",
            field=field,
        )
        return

    expected = "met" if target_met else "missed"
    if claim_semantics == expected:
        report.add(
            "claim.metric.target_semantics",
            PASS,
            f"Claim target status matches recomputed target_met={target_met}.",
        )
    else:
        report.add(
            "claim.metric.target_semantics",
            FAIL,
            (
                f"Claim says target was {claim_semantics}, but the contract/evidence "
                f"recompute target status as {expected}."
            ),
            suggestion="Align target-status wording with the declared threshold and selected observation.",
            field=field,
        )
