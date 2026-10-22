"""Audit explicit analysis-scope identity and row-level scope consistency."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from .analysis_scope import (
    ANALYSIS_SCOPE_INTENTS,
    chart_analysis_scope_contract,
    parse_analysis_scope_contract,
    scope_basis_status,
)
from .audit import FAIL, PASS, AuditReport


def audit_analysis_scope_chart(report: AuditReport, chart: Any) -> None:
    if getattr(chart, "intent", None) not in ANALYSIS_SCOPE_INTENTS:
        return

    raw = chart_analysis_scope_contract(chart)
    if raw is None:
        return

    try:
        contract = parse_analysis_scope_contract(
            {"usermeta": {"analysis_scope_contract": raw}}
        )
    except ValueError as exc:
        report.add(
            "contract.analysis_scope.identity",
            FAIL,
            str(exc).replace(
                "usermeta.analysis_scope_contract.",
                "analysis scope contract ",
            ),
            suggestion=(
                "Declare scope_id, scope_definition, and scope_version together; "
                "scope_basis_field/value are optional but must be paired."
            ),
            field="scope_id",
        )
        return

    report.add(
        "contract.analysis_scope.identity",
        PASS,
        (
            f"Analysis scope {contract['scope_id']!r} declares version "
            f"{contract['scope_version']!r}."
        ),
    )
    _audit_basis(
        report,
        chart.data,
        contract,
        surface_field="scope_basis_field",
    )


def audit_analysis_scope_spec(
    report: AuditReport,
    spec: Mapping[str, Any],
    frame: pd.DataFrame | None,
) -> None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or "analysis_scope_contract" not in usermeta:
        return

    try:
        contract = parse_analysis_scope_contract(spec)
    except ValueError as exc:
        report.add(
            "contract.analysis_scope.identity",
            FAIL,
            str(exc),
            suggestion="Use the exact closed version-1 analysis scope contract schema.",
            field="usermeta.analysis_scope_contract",
        )
        return

    if contract is None:
        return

    report.add(
        "contract.analysis_scope.identity",
        PASS,
        (
            f"Analysis scope {contract['scope_id']!r} declares version "
            f"{contract['scope_version']!r}."
        ),
    )

    if contract["scope_basis_field"] is not None and frame is None:
        report.add(
            "data.analysis_scope.basis",
            FAIL,
            (
                "Analysis scope contract declares a row-level basis field but no "
                "reconstructable evidence was supplied."
            ),
            suggestion="Provide the evidence rows so scope identity can be checked.",
            field="usermeta.analysis_scope_contract.scope_basis_field",
        )
        return

    if frame is not None:
        _audit_basis(
            report,
            frame,
            contract,
            surface_field="usermeta.analysis_scope_contract.scope_basis_field",
        )


def _audit_basis(
    report: AuditReport,
    frame: pd.DataFrame,
    contract: Mapping[str, Any],
    *,
    surface_field: str,
) -> None:
    basis_field = contract["scope_basis_field"]
    basis_value = contract["scope_basis_value"]
    if basis_field is None or basis_value is None:
        return

    ok, message = scope_basis_status(
        frame,
        basis_field=basis_field,
        basis_value=basis_value,
    )
    report.add(
        "data.analysis_scope.basis",
        PASS if ok else FAIL,
        message,
        suggestion=(
            None
            if ok
            else (
                "Use one analysis-scope identity across the artifact or split "
                "different filtered/cohort universes into separate artifacts."
            )
        ),
        field=surface_field,
    )
