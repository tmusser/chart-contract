"""Audit metric directionality and evaluative comparison claims."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .audit import FAIL, PASS, WARN, AuditReport, _encoding_field, _encoding_type, _iter_encoding_definitions
from .comparison import comparison_declaration, build_comparison_summary, parse_comparison_contract
from .directionality import (
    DIRECTIONALITY_CONTRACT_KEY,
    DIRECTIONALITY_INTENTS,
    chart_directionality_contract,
    explicit_evaluative_claim,
    movement_semantics,
    parse_directionality_contract,
)


def audit_directionality_chart(report: AuditReport, chart: Any) -> None:
    if getattr(chart, "intent", None) not in DIRECTIONALITY_INTENTS:
        return

    claim_semantics = explicit_evaluative_claim(getattr(chart, "claim", None))
    raw = chart_directionality_contract(chart)

    if raw is None:
        if claim_semantics is not None:
            report.add(
                "claim.metric.directionality",
                WARN,
                "Claim uses evaluative better/worse wording but no metric directionality is declared.",
                suggestion=(
                    "Declare metric_direction='higher_is_better', "
                    "'lower_is_better', or 'neutral' before making evaluative claims."
                ),
                field="metric_direction",
            )
        return

    try:
        contract = parse_directionality_contract(
            {"usermeta": {DIRECTIONALITY_CONTRACT_KEY: raw}}
        )
    except ValueError as exc:
        report.add(
            "contract.metric.directionality",
            FAIL,
            str(exc).replace(
                "usermeta.directionality_contract.",
                "directionality contract ",
            ),
            field="metric_direction",
        )
        return

    if contract["metric_field"] != getattr(chart, "y", None):
        report.add(
            "contract.metric.directionality",
            FAIL,
            "Directionality contract is not bound to the chart quantitative metric.",
            field="y",
        )
        return

    report.add(
        "contract.metric.directionality",
        PASS,
        (
            f"Metric {contract['metric_field']!r} declares "
            f"direction={contract['direction']!r}."
        ),
    )

    if claim_semantics is None:
        return
    if claim_semantics == "ambiguous":
        report.add(
            "claim.metric.directionality",
            FAIL,
            "Claim mixes improvement and worsening language and cannot be adjudicated deterministically.",
            suggestion="Use one unambiguous evaluative direction in the claim.",
            field="claim",
        )
        return

    declaration = comparison_declaration(chart)
    if declaration is None:
        report.add(
            "claim.metric.directionality",
            WARN,
            "Evaluative claim has metric directionality but no explicit comparison baseline.",
            suggestion=(
                "Declare baseline_field, baseline_value, target_value, change_type, "
                "and declared_change so better/worse semantics are reproducible."
            ),
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
    except ValueError:
        return

    _add_claim_finding(
        report,
        claim_semantics,
        contract["direction"],
        summary.baseline_metric_value,
        summary.target_metric_value,
        field="claim",
    )


def audit_directionality_spec(
    report: AuditReport,
    spec: Mapping[str, Any],
    encoding: Any,
    claim: str | None,
) -> None:
    usermeta = spec.get("usermeta")
    has_contract = isinstance(usermeta, Mapping) and DIRECTIONALITY_CONTRACT_KEY in usermeta
    claim_semantics = explicit_evaluative_claim(claim)

    if not has_contract:
        if claim_semantics is not None:
            report.add(
                "claim.metric.directionality",
                WARN,
                "Claim uses evaluative better/worse wording but the spec has no directionality_contract.",
                suggestion=(
                    "Add usermeta.directionality_contract before making evaluative claims."
                ),
                field="usermeta.directionality_contract",
            )
        return

    try:
        contract = parse_directionality_contract(spec)
    except ValueError as exc:
        report.add(
            "contract.metric.directionality",
            FAIL,
            str(exc),
            suggestion="Use the exact closed version-1 directionality contract schema.",
            field="usermeta.directionality_contract",
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
            "contract.metric.directionality",
            FAIL,
            "directionality_contract.metric_field is not a shown quantitative field.",
            field="usermeta.directionality_contract.metric_field",
        )
        return

    report.add(
        "contract.metric.directionality",
        PASS,
        (
            f"Metric {contract['metric_field']!r} declares "
            f"direction={contract['direction']!r}."
        ),
    )

    if claim_semantics is None:
        return
    if claim_semantics == "ambiguous":
        report.add(
            "claim.metric.directionality",
            FAIL,
            "Claim mixes improvement and worsening language and cannot be adjudicated deterministically.",
            suggestion="Use one unambiguous evaluative direction in the claim.",
            field="claim",
        )
        return

    try:
        comparison = parse_comparison_contract(spec)
    except ValueError:
        return

    if comparison is None:
        report.add(
            "claim.metric.directionality",
            WARN,
            "Evaluative claim has metric directionality but no explicit comparison_contract.",
            suggestion=(
                "Add an explicit baseline and target comparison before making better/worse claims."
            ),
            field="usermeta.comparison_contract",
        )
        return

    if comparison["metric_field"] != contract["metric_field"]:
        report.add(
            "claim.metric.directionality",
            FAIL,
            "Directionality and comparison contracts are bound to different metric fields.",
            field="usermeta.directionality_contract.metric_field",
        )
        return

    _add_claim_finding(
        report,
        claim_semantics,
        contract["direction"],
        float(comparison["baseline_metric_value"]),
        float(comparison["target_metric_value"]),
        field="claim",
    )


def _add_claim_finding(
    report: AuditReport,
    claim_semantics: str,
    direction: str,
    baseline: float,
    target: float,
    *,
    field: str,
) -> None:
    observed = movement_semantics(baseline, target, direction=direction)

    if observed == "neutral":
        report.add(
            "claim.metric.directionality",
            FAIL,
            "Claim makes an evaluative better/worse judgment but metric direction is declared neutral.",
            suggestion="Use descriptive increase/decrease wording or declare a justified directional metric.",
            field=field,
        )
        return

    if observed == "unchanged":
        report.add(
            "claim.metric.directionality",
            FAIL,
            "Claim makes an evaluative better/worse judgment but baseline and target metric values are unchanged.",
            suggestion="Use neutral wording for an unchanged comparison.",
            field=field,
        )
        return

    if observed == claim_semantics:
        report.add(
            "claim.metric.directionality",
            PASS,
            (
                f"Claim {claim_semantics} semantics match direction={direction!r} "
                f"for baseline {baseline:g} -> target {target:g}."
            ),
        )
    else:
        report.add(
            "claim.metric.directionality",
            FAIL,
            (
                f"Claim says {claim_semantics}, but direction={direction!r} makes "
                f"baseline {baseline:g} -> target {target:g} a {observed}."
            ),
            suggestion="Align evaluative wording with the declared metric direction and observed comparison.",
            field=field,
        )
