"""Audit explicit uncertainty interval semantics and visible bindings."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from .audit import FAIL, PASS, WARN, AuditReport
from .uncertainty import (
    UNCERTAINTY_INTENTS,
    chart_uncertainty_contract,
    interval_bounds_status,
    interval_claim_status,
    parse_uncertainty_contract,
    spec_has_interval_binding,
)


def audit_uncertainty_chart(report: AuditReport, chart: Any) -> None:
    if getattr(chart, "intent", None) not in UNCERTAINTY_INTENTS:
        return

    raw = chart_uncertainty_contract(chart)
    if raw is None:
        severity, message = interval_claim_status(getattr(chart, "claim", None), None)
        if severity == "WARN":
            report.add(
                "claim.uncertainty.semantics",
                WARN,
                message or "Explicit interval claim lacks metadata.",
                suggestion=(
                    "Declare interval lower/upper fields, kind, level, and method."
                ),
                field="claim",
            )
        return

    try:
        contract = parse_uncertainty_contract(
            {"usermeta": {"uncertainty_contract": raw}}
        )
    except ValueError as exc:
        report.add(
            "contract.uncertainty.interval",
            FAIL,
            str(exc).replace(
                "usermeta.uncertainty_contract.",
                "uncertainty contract ",
            ),
            suggestion=(
                "Declare one closed interval contract with estimate/lower/upper fields, "
                "interval kind, level, and method."
            ),
            field="interval_kind",
        )
        return

    if contract["estimate_field"] != getattr(chart, "y", None):
        report.add(
            "contract.uncertainty.interval",
            FAIL,
            "Uncertainty estimate field is not bound to the chart quantitative metric.",
            suggestion="Bind interval metadata to the chart y estimate.",
            field="y",
        )
        return

    report.add(
        "contract.uncertainty.interval",
        PASS,
        (
            f"Declared {contract['interval_level'] * 100:g}% "
            f"{contract['interval_kind']} interval using method "
            f"{contract['interval_method']!r}."
        ),
    )

    ok, message = interval_bounds_status(
        chart.data,
        estimate_field=contract["estimate_field"],
        lower_field=contract["lower_field"],
        upper_field=contract["upper_field"],
    )
    report.add(
        "data.uncertainty.bounds",
        PASS if ok else FAIL,
        message,
        suggestion=(
            None
            if ok
            else "Provide complete finite bounds satisfying lower <= estimate <= upper."
        ),
        field="interval_lower_field",
    )

    severity, claim_message = interval_claim_status(
        getattr(chart, "claim", None),
        contract,
    )
    if severity is not None:
        report.add(
            "claim.uncertainty.semantics",
            PASS if severity == "PASS" else FAIL,
            claim_message or "Uncertainty claim semantics disagree with metadata.",
            suggestion=(
                None
                if severity == "PASS"
                else "Align explicit claim wording with the declared interval kind and level."
            ),
            field="claim",
        )


def audit_uncertainty_spec(
    report: AuditReport,
    spec: Mapping[str, Any],
    frame: pd.DataFrame | None,
    claim: str | None,
) -> None:
    usermeta = spec.get("usermeta")
    has_contract = isinstance(usermeta, Mapping) and "uncertainty_contract" in usermeta

    if not has_contract:
        severity, message = interval_claim_status(claim, None)
        if severity == "WARN":
            report.add(
                "claim.uncertainty.semantics",
                WARN,
                message or "Explicit interval claim lacks metadata.",
                suggestion="Add a closed usermeta.uncertainty_contract.",
                field="claim",
            )
        return

    try:
        contract = parse_uncertainty_contract(spec)
    except ValueError as exc:
        report.add(
            "contract.uncertainty.interval",
            FAIL,
            str(exc),
            suggestion="Use the exact closed version-1 uncertainty contract schema.",
            field="usermeta.uncertainty_contract",
        )
        return

    if contract is None:
        return

    report.add(
        "contract.uncertainty.interval",
        PASS,
        (
            f"Declared {contract['interval_level'] * 100:g}% "
            f"{contract['interval_kind']} interval using method "
            f"{contract['interval_method']!r}."
        ),
    )

    if frame is None:
        report.add(
            "data.uncertainty.bounds",
            FAIL,
            "Uncertainty contract requires reconstructable estimate/lower/upper evidence.",
            suggestion="Provide the underlying data used by the interval-bearing spec.",
            field="usermeta.uncertainty_contract",
        )
    else:
        ok, message = interval_bounds_status(
            frame,
            estimate_field=contract["estimate_field"],
            lower_field=contract["lower_field"],
            upper_field=contract["upper_field"],
        )
        report.add(
            "data.uncertainty.bounds",
            PASS if ok else FAIL,
            message,
            suggestion=(
                None
                if ok
                else "Provide complete finite bounds satisfying lower <= estimate <= upper."
            ),
            field="usermeta.uncertainty_contract",
        )

    if spec_has_interval_binding(
        spec,
        estimate_field=contract["estimate_field"],
        lower_field=contract["lower_field"],
        upper_field=contract["upper_field"],
    ):
        report.add(
            "visual.uncertainty.interval",
            PASS,
            "Spec visibly binds the declared estimate plus lower/upper interval fields.",
        )
    else:
        report.add(
            "visual.uncertainty.interval",
            FAIL,
            "Spec declares uncertainty metadata but does not visibly encode the declared estimate and interval bounds.",
            suggestion=(
                "Encode the declared lower/upper fields as y/y2 or x/x2 on a rule layer."
            ),
            field="usermeta.uncertainty_contract",
        )

    severity, claim_message = interval_claim_status(claim, contract)
    if severity is not None:
        report.add(
            "claim.uncertainty.semantics",
            PASS if severity == "PASS" else FAIL,
            claim_message or "Uncertainty claim semantics disagree with metadata.",
            suggestion=(
                None
                if severity == "PASS"
                else "Align explicit claim wording with the declared interval kind and level."
            ),
            field="claim",
        )
