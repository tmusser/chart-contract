"""Audit explicit population scope, sampling, weights, and generalization intent."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from .audit import FAIL, PASS, WARN, AuditReport
from .population_sampling import (
    POPULATION_INTENTS,
    chart_population_contract,
    claim_implies_sampling_scope,
    generalization_status,
    parse_population_contract,
    sample_member_status,
    weight_status,
)


def audit_population_chart(report: AuditReport, chart: Any) -> None:
    if getattr(chart, "intent", None) not in POPULATION_INTENTS:
        return

    raw = chart_population_contract(chart)
    if raw is None:
        if claim_implies_sampling_scope(getattr(chart, "claim", None)):
            report.add(
                "contract.population.scope",
                WARN,
                "Claim explicitly names sample/census scope but no population contract is declared.",
                suggestion=(
                    "Declare sample/census scope, target population, sample size, "
                    "sampling method, and generalization intent."
                ),
                field="evidence_scope",
            )
        return

    try:
        contract = parse_population_contract(
            {"usermeta": {"population_contract": raw}}
        )
    except ValueError as exc:
        report.add(
            "contract.population.scope",
            FAIL,
            str(exc).replace(
                "usermeta.population_contract.",
                "population contract ",
            ),
            suggestion=(
                "Declare one closed census/sample contract with population identity, "
                "sample size, sampling method, and explicit generalization intent."
            ),
            field="evidence_scope",
        )
        return

    report.add(
        "contract.population.scope",
        PASS,
        _scope_message(contract),
    )
    _audit_evidence(
        report,
        chart.data,
        contract,
        member_surface="sample_member_field",
        weight_surface="weight_field",
    )
    _audit_generalization(report, contract)


def audit_population_spec(
    report: AuditReport,
    spec: Mapping[str, Any],
    frame: pd.DataFrame | None,
    claim: str | None,
) -> None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or "population_contract" not in usermeta:
        if claim_implies_sampling_scope(claim):
            report.add(
                "contract.population.scope",
                WARN,
                "Claim explicitly names sample/census scope but no population contract is declared.",
                suggestion=(
                    "Add usermeta.population_contract with sample/census scope, target "
                    "population, sample size, sampling method, and generalization intent."
                ),
                field="usermeta.population_contract",
            )
        return

    try:
        contract = parse_population_contract(spec)
    except ValueError as exc:
        report.add(
            "contract.population.scope",
            FAIL,
            str(exc),
            suggestion="Use the exact closed version-1 population contract schema.",
            field="usermeta.population_contract",
        )
        return

    if contract is None:
        return

    report.add(
        "contract.population.scope",
        PASS,
        _scope_message(contract),
    )

    requires_frame = (
        contract["sample_member_field"] is not None
        or contract["weight_field"] is not None
    )
    if requires_frame and frame is None:
        if contract["sample_member_field"] is not None:
            report.add(
                "data.population.sample_count",
                FAIL,
                (
                    "Population contract declares a sample member field but no "
                    "reconstructable evidence was supplied."
                ),
                suggestion="Provide the row-level sample evidence or omit the unverified member field.",
                field="usermeta.population_contract.sample_member_field",
            )
        if contract["weight_field"] is not None:
            report.add(
                "data.population.weights",
                FAIL,
                (
                    "Population contract declares a weight field but no "
                    "reconstructable evidence was supplied."
                ),
                suggestion="Provide the weighted evidence rows so weight values can be checked.",
                field="usermeta.population_contract.weight_field",
            )
    elif frame is not None:
        _audit_evidence(
            report,
            frame,
            contract,
            member_surface="usermeta.population_contract.sample_member_field",
            weight_surface="usermeta.population_contract.weight_field",
        )

    _audit_generalization(report, contract)


def _scope_message(contract: Mapping[str, Any]) -> str:
    population_size = contract["population_size"]
    population_text = (
        f" of declared population size {population_size}"
        if population_size is not None
        else " of a population with undeclared size"
    )
    return (
        f"Evidence scope is {contract['evidence_scope']!r} for "
        f"{contract['population']!r}: sample_size={contract['sample_size']}"
        f"{population_text}, sampling_method={contract['sampling_method']!r}."
    )


def _audit_evidence(
    report: AuditReport,
    frame: pd.DataFrame,
    contract: Mapping[str, Any],
    *,
    member_surface: str,
    weight_surface: str,
) -> None:
    member_field = contract["sample_member_field"]
    if member_field is not None:
        ok, message = sample_member_status(
            frame,
            member_field=member_field,
            sample_size=contract["sample_size"],
        )
        report.add(
            "data.population.sample_count",
            PASS if ok else FAIL,
            message,
            suggestion=(
                None
                if ok
                else (
                    "Provide one unique non-null member identifier per sampled unit "
                    "or correct the declared sample_size."
                )
            ),
            field=member_surface,
        )

    weight_field = contract["weight_field"]
    if weight_field is not None:
        ok, message = weight_status(frame, weight_field=weight_field)
        report.add(
            "data.population.weights",
            PASS if ok else FAIL,
            message,
            suggestion=(
                None
                if ok
                else "Provide complete, finite, strictly positive sampling weights."
            ),
            field=weight_surface,
        )


def _audit_generalization(
    report: AuditReport,
    contract: Mapping[str, Any],
) -> None:
    severity, message = generalization_status(contract)
    report.add(
        "claim.population.generalization",
        PASS if severity == "PASS" else WARN,
        message,
        suggestion=(
            None
            if severity == "PASS"
            else (
                "Narrow the artifact to the observed sample or document a defensible "
                "sampling/weighting design before generalizing to the population."
            )
        ),
        field="generalizes_to_population",
    )
