"""Audit numerator/denominator identity for ratio-like metrics."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from .audit import (
    FAIL,
    PASS,
    WARN,
    AuditReport,
    _encoding_field,
    _encoding_type,
    _iter_encoding_definitions,
)
from .contracts import is_ratio_like_unit
from .ratio import (
    chart_ratio_contract,
    denominator_basis_status,
    parse_ratio_contract,
)


def audit_ratio_chart(report: AuditReport, chart: Any) -> None:
    raw_contract = chart_ratio_contract(chart)
    ratio_like = is_ratio_like_unit(getattr(chart, "unit", None))

    if raw_contract is None:
        if ratio_like:
            report.add(
                "contract.ratio.denominator",
                WARN,
                "Ratio-like metric does not declare numerator and denominator identities.",
                suggestion=(
                    "Declare numerator=... and denominator=... so viewers know what population "
                    "the rate, ratio, or percentage is 'of'."
                ),
                field="denominator",
            )
        return

    try:
        contract = parse_ratio_contract({"usermeta": {"ratio_contract": raw_contract}})
    except ValueError as exc:
        report.add(
            "contract.ratio.denominator",
            FAIL,
            str(exc).replace("usermeta.ratio_contract.", "ratio contract "),
            suggestion="Declare non-empty numerator and denominator identities; cohort and basis field are optional.",
            field="denominator",
        )
        return

    if contract["metric_field"] != getattr(chart, "y", None):
        report.add(
            "contract.ratio.denominator",
            FAIL,
            "Ratio contract metric field does not match the chart quantitative metric.",
            suggestion="Bind ratio semantics to the chart y metric.",
            field="y",
        )
        return

    report.add(
        "contract.ratio.denominator",
        PASS,
        (
            f"Ratio metric declares numerator {contract['numerator']!r} over "
            f"denominator {contract['denominator']!r}"
            + (
                f" for cohort {contract['cohort']!r}."
                if contract["cohort"] is not None
                else "."
            )
        ),
    )

    _audit_basis(
        report,
        chart.data,
        contract,
        surface_field="denominator_basis_field",
    )


def audit_ratio_spec(
    report: AuditReport,
    spec: Mapping[str, Any],
    encoding: Any,
    frame: pd.DataFrame | None,
    unit: str | None,
) -> None:
    raw_usermeta = spec.get("usermeta")
    has_contract = isinstance(raw_usermeta, Mapping) and "ratio_contract" in raw_usermeta
    ratio_like = is_ratio_like_unit(unit)

    if not has_contract:
        if ratio_like:
            report.add(
                "contract.ratio.denominator",
                WARN,
                "Ratio-like spec metric does not declare numerator and denominator identities.",
                suggestion=(
                    "Add usermeta.ratio_contract with metric_field, numerator, denominator, "
                    "and optional cohort/denominator_basis_field."
                ),
                field="usermeta.ratio_contract",
            )
        return

    try:
        contract = parse_ratio_contract(spec)
    except ValueError as exc:
        report.add(
            "contract.ratio.denominator",
            FAIL,
            str(exc),
            suggestion="Use the exact closed version-1 ratio contract schema.",
            field="usermeta.ratio_contract",
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
            "contract.ratio.denominator",
            FAIL,
            (
                f"Ratio contract metric field {contract['metric_field']!r} is not an encoded "
                "quantitative field in the audited spec."
            ),
            suggestion="Bind ratio_contract.metric_field to the quantitative metric shown by the spec.",
            field="usermeta.ratio_contract.metric_field",
        )
        return

    report.add(
        "contract.ratio.denominator",
        PASS,
        (
            f"Ratio spec declares numerator {contract['numerator']!r} over "
            f"denominator {contract['denominator']!r}"
            + (
                f" for cohort {contract['cohort']!r}."
                if contract["cohort"] is not None
                else "."
            )
        ),
    )

    if contract["denominator_basis_field"] is not None and frame is None:
        report.add(
            "data.ratio.denominator_basis",
            FAIL,
            "Ratio contract declares a denominator basis field but no reconstructable evidence was supplied.",
            suggestion="Provide the full evidence rows so denominator identity can be checked.",
            field="usermeta.ratio_contract.denominator_basis_field",
        )
        return

    if frame is not None:
        _audit_basis(
            report,
            frame,
            contract,
            surface_field="usermeta.ratio_contract.denominator_basis_field",
        )


def _audit_basis(
    report: AuditReport,
    frame: pd.DataFrame,
    contract: Mapping[str, Any],
    *,
    surface_field: str,
) -> None:
    basis_field = contract.get("denominator_basis_field")
    if basis_field is None:
        return

    ok, message = denominator_basis_status(
        frame,
        basis_field=basis_field,
        denominator=contract["denominator"],
    )
    report.add(
        "data.ratio.denominator_basis",
        PASS if ok else FAIL,
        message,
        suggestion=(
            None
            if ok
            else "Use one denominator identity for the compared metric or split incompatible metrics into separate charts."
        ),
        field=surface_field,
    )
