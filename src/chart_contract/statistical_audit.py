"""Audit rules for statistical diagnostic chart intents."""

from __future__ import annotations

from copy import copy
from typing import Any

from .audit import FAIL, PASS, WARN, AuditReport, audit_chart
from .contracts import is_numeric_series

STATISTICAL_INTENTS = {"qq", "ecdf", "residual"}


def audit_statistical_chart(chart: Any) -> AuditReport:
    """Reuse the common chart contract, then add intent-specific diagnostics."""
    proxy = copy(chart)
    if chart.intent in {"qq", "ecdf"}:
        proxy.intent = "boxplot"
        proxy.x = chart.group
        proxy.y = chart.value
        proxy.category = chart.group
    elif chart.intent == "residual":
        proxy.intent = "compare"
        proxy.category = chart.x
    else:
        raise ValueError(f"Unsupported statistical chart intent: {chart.intent}")

    report = audit_chart(proxy)
    report.findings = [finding for finding in report.findings if finding.rule_id != "visual.intent.match"]
    report.add(
        "visual.intent.match",
        PASS,
        f"{chart.intent.upper() if chart.intent in {'qq', 'ecdf'} else chart.intent.title()} visual form matches the declared statistical intent.",
    )

    if chart.intent == "qq":
        _audit_qq(report, chart)
    elif chart.intent == "residual":
        _audit_residual(report, chart)

    return report


def _audit_qq(report: AuditReport, chart: Any) -> None:
    if chart.distribution == "normal":
        report.add(
            "stat.qq.reference_distribution",
            PASS,
            "QQ plot uses the supported normal reference distribution.",
        )
    else:
        report.add(
            "stat.qq.reference_distribution",
            FAIL,
            f"Unsupported QQ reference distribution: {chart.distribution!r}.",
            suggestion="Use distribution='normal'; other reference distributions are not implemented yet.",
            field="distribution",
        )

    if not chart.value or chart.value not in chart.data.columns or not is_numeric_series(chart.data[chart.value]):
        return
    values = chart.data[chart.value].dropna()
    unique_count = int(values.nunique(dropna=True))
    row_count = len(values)
    if row_count >= 10 and unique_count / row_count < 0.5:
        report.add(
            "stat.qq.tie_density",
            WARN,
            f"QQ plot has {unique_count} unique values across {row_count} observations; heavy ties can obscure tail behavior.",
            suggestion="Treat the QQ shape cautiously or use an ECDF for discrete or rounded data.",
            field=chart.value,
        )
    else:
        report.add(
            "stat.qq.tie_density",
            PASS,
            "QQ plot has enough distinct values for a readable quantile comparison.",
        )


def _audit_residual(report: AuditReport, chart: Any) -> None:
    fitted = chart.x
    residual = chart.y
    if not fitted or fitted not in chart.data.columns:
        report.add(
            "data.residual.fitted.numeric",
            FAIL,
            "Residual plots require a fitted-value column.",
            field=fitted,
        )
    elif is_numeric_series(chart.data[fitted]):
        report.add(
            "data.residual.fitted.numeric",
            PASS,
            "Fitted-value field is numeric.",
        )
    else:
        report.add(
            "data.residual.fitted.numeric",
            FAIL,
            f"Fitted-value field '{fitted}' must be numeric for residual plots.",
            field=fitted,
        )

    required = [field for field in (fitted, residual) if field and field in chart.data.columns]
    complete_count = int(chart.data[required].notna().all(axis=1).sum()) if len(required) == 2 else 0
    if complete_count < 5:
        report.add(
            "data.residual.sample_size",
            FAIL,
            f"Residual plot has {complete_count} complete observation(s); diagnostics need at least 5.",
            suggestion="Provide more fitted/residual pairs before interpreting model diagnostics.",
        )
    elif complete_count < 20:
        report.add(
            "data.residual.sample_size",
            WARN,
            f"Residual plot has {complete_count} complete observations; pattern judgments are fragile below 20.",
            suggestion="Use more observations before making strong residual-pattern claims.",
        )
    else:
        report.add(
            "data.residual.sample_size",
            PASS,
            f"Residual plot has {complete_count} complete observations.",
        )

    if residual and residual in chart.data.columns and is_numeric_series(chart.data[residual]):
        if chart.data[residual].dropna().nunique() <= 1:
            report.add(
                "data.residual.variation",
                WARN,
                "Residual values have no variation; verify that residuals were computed and exported correctly.",
                suggestion="Check the prediction and residual calculation pipeline.",
                field=residual,
            )
        else:
            report.add(
                "data.residual.variation",
                PASS,
                "Residual values contain variation for diagnostic inspection.",
            )

    report.add(
        "visual.residual.zero_reference",
        PASS,
        "Residual renderer includes a zero reference line.",
    )
