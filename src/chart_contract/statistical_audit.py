"""Audit rules for statistical diagnostic chart intents."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from copy import copy
from statistics import NormalDist, fmean, stdev
from typing import Any

import pandas as pd

from .audit import FAIL, PASS, WARN, AuditReport, audit_chart
from .contracts import is_numeric_series

STATISTICAL_INTENTS = {"qq", "ecdf", "residual"}
QQ_THEORETICAL_FIELD = "_theoretical_quantile"
QQ_SAMPLE_FIELD = "_sample_quantile"
QQ_REFERENCE_FIELD = "_reference_quantile"
QQ_TAIL_DEVIATION_WARN_RATIO = 0.8
RESIDUAL_CORRELATION_WARN = 0.5
RESIDUAL_THIRDS_SHIFT_WARN = 1.0
NORMALITY_TERMS = ("normal", "normally distributed", "gaussian")
NO_PATTERN_TERMS = (
    "no pattern",
    "no obvious pattern",
    "no structure",
    "randomly scattered",
    "random scatter",
    "well behaved",
    "well-behaved",
    "centered around zero",
    "centred around zero",
)


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


def audit_statistical_spec(
    report: AuditReport,
    spec: Mapping[str, Any],
    frame: pd.DataFrame | None,
    claim: str,
) -> None:
    """Apply first-party statistical semantics to an audited Vega-Lite spec."""
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping):
        return
    intent = usermeta.get("chart_contract_intent")
    if intent not in STATISTICAL_INTENTS:
        return

    if intent == "qq":
        _audit_qq_spec(report, spec, frame, claim, usermeta)
    elif intent == "residual":
        _audit_residual_spec(report, spec, frame, claim)


def _audit_qq(report: AuditReport, chart: Any) -> None:
    distribution_ok = chart.distribution == "normal"
    if distribution_ok:
        report.add(
            "stat.qq.reference_distribution",
            PASS,
            "QQ plot uses the supported normal reference distribution.",
        )
        report.add(
            "visual.qq.reference_line",
            PASS,
            "QQ renderer includes a fitted normal location-scale reference line.",
        )
    else:
        report.add(
            "stat.qq.reference_distribution",
            FAIL,
            f"Unsupported QQ reference distribution: {chart.distribution!r}.",
            suggestion="Use distribution='normal'; other reference distributions are not implemented yet.",
            field="distribution",
        )
        report.add(
            "visual.qq.reference_line",
            FAIL,
            "QQ reference-line semantics are not defined for the requested distribution.",
            suggestion="Use the supported normal reference or implement and test the requested reference distribution first.",
            field="distribution",
        )

    if not chart.value or chart.value not in chart.data.columns or not is_numeric_series(chart.data[chart.value]):
        return

    values = chart.data[chart.value].dropna()
    _audit_qq_ties(report, values, chart.value)
    _audit_qq_claim_support(report, chart.data, chart.value, chart.group, chart.claim)


def _audit_qq_spec(
    report: AuditReport,
    spec: Mapping[str, Any],
    frame: pd.DataFrame | None,
    claim: str,
    usermeta: Mapping[str, Any],
) -> None:
    distribution = usermeta.get("qq_reference_distribution")
    distribution_ok = distribution == "normal"
    if distribution_ok:
        report.add(
            "stat.qq.reference_distribution",
            PASS,
            "QQ spec declares the supported normal reference distribution.",
        )
    else:
        report.add(
            "stat.qq.reference_distribution",
            FAIL,
            f"QQ spec declares an unsupported or missing reference distribution: {distribution!r}.",
            suggestion="Set usermeta.qq_reference_distribution to 'normal' for the supported contract.",
            field="usermeta.qq_reference_distribution",
        )

    reference_view = _find_view(
        spec,
        mark="line",
        x_field=QQ_THEORETICAL_FIELD,
        y_field=QQ_REFERENCE_FIELD,
    )
    if distribution_ok and reference_view is not None:
        report.add(
            "visual.qq.reference_line",
            PASS,
            "QQ spec includes the expected fitted normal reference line.",
        )
    else:
        report.add(
            "visual.qq.reference_line",
            FAIL,
            "QQ spec is missing an appropriate fitted normal reference line.",
            suggestion=(
                f"Add a line layer encoding {QQ_THEORETICAL_FIELD} against {QQ_REFERENCE_FIELD} "
                "and declare the normal reference distribution."
            ),
            field="layer",
        )

    point_view = _find_view(spec, mark="point", y_field=QQ_SAMPLE_FIELD)
    sample_field = _encoding_field(_encoding(point_view, "y")) if point_view is not None else None
    if frame is None or not sample_field or sample_field not in frame.columns:
        return
    values = frame[sample_field]
    if not is_numeric_series(values):
        return

    valid = values.dropna()
    _audit_diagnostic_sample_size(report, "QQ spec", len(valid))
    _audit_qq_ties(report, valid, sample_field)
    _audit_qq_claim_support(report, frame, sample_field, None, claim)


def _audit_qq_ties(report: AuditReport, values: pd.Series, field: str) -> None:
    unique_count = int(values.nunique(dropna=True))
    row_count = len(values)
    if row_count >= 10 and unique_count / row_count < 0.5:
        report.add(
            "stat.qq.tie_density",
            WARN,
            f"QQ plot has {unique_count} unique values across {row_count} observations; heavy ties can obscure tail behavior.",
            suggestion="Treat the QQ shape cautiously or use an ECDF for discrete or rounded data.",
            field=field,
        )
    else:
        report.add(
            "stat.qq.tie_density",
            PASS,
            "QQ plot has enough distinct values for a readable quantile comparison.",
        )


def _audit_qq_claim_support(
    report: AuditReport,
    frame: pd.DataFrame,
    value_field: str,
    group_field: str | None,
    claim: str,
) -> None:
    ratios: list[float] = []
    if group_field and group_field in frame.columns:
        groups = (group[value_field].dropna() for _, group in frame.groupby(group_field, dropna=False, sort=False))
    else:
        groups = (frame[value_field].dropna(),)

    for values in groups:
        ratio = _qq_tail_deviation_ratio(values)
        if ratio is not None:
            ratios.append(ratio)
    if not ratios:
        return

    worst_ratio = max(ratios)
    asserts_normality = _contains_any(claim, NORMALITY_TERMS)
    if worst_ratio >= QQ_TAIL_DEVIATION_WARN_RATIO:
        message = (
            f"QQ outer quantiles deviate from the fitted normal line by {worst_ratio:.2f} sample standard deviations."
        )
        if asserts_normality:
            message += " The claim overstates normal compatibility."
        report.add(
            "claim.qq.normality_support",
            WARN,
            message,
            suggestion="Describe the observed tail departure and avoid claiming the data are normal.",
            field="claim",
        )
    else:
        report.add(
            "claim.qq.normality_support",
            PASS,
            "QQ tail alignment does not contradict the stated normal-reference claim at the deterministic threshold.",
        )


def _qq_tail_deviation_ratio(values: pd.Series) -> float | None:
    ordered = sorted(float(value) for value in values.dropna())
    if len(ordered) < 5:
        return None
    scale = stdev(ordered)
    if scale == 0:
        return None

    center = fmean(ordered)
    theoretical = [
        NormalDist().inv_cdf((index - 0.5) / len(ordered))
        for index in range(1, len(ordered) + 1)
    ]
    expected = [center + scale * quantile for quantile in theoretical]
    tail_count = max(1, len(ordered) // 5)
    tail_indexes = [*range(tail_count), *range(len(ordered) - tail_count, len(ordered))]
    return max(abs(ordered[index] - expected[index]) for index in tail_indexes) / scale


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

    complete = _complete_residual_frame(chart.data, fitted, residual)
    _audit_diagnostic_sample_size(report, "Residual plot", len(complete), rule_id="data.residual.sample_size")
    _audit_residual_variation(report, complete, residual)
    _audit_residual_claim_support(report, complete, fitted, residual, chart.claim)

    report.add(
        "visual.residual.zero_reference",
        PASS,
        "Residual renderer includes a zero reference line.",
    )


def _audit_residual_spec(
    report: AuditReport,
    spec: Mapping[str, Any],
    frame: pd.DataFrame | None,
    claim: str,
) -> None:
    point_view = _find_view(spec, mark="point")
    fitted = _encoding_field(_encoding(point_view, "x")) if point_view is not None else None
    residual = _encoding_field(_encoding(point_view, "y")) if point_view is not None else None

    if frame is None or not fitted or fitted not in frame.columns:
        report.add(
            "data.residual.fitted.numeric",
            FAIL,
            "Residual spec requires a numeric fitted-value field with supplied data.",
            field=fitted,
        )
        complete = pd.DataFrame()
    elif is_numeric_series(frame[fitted]):
        report.add("data.residual.fitted.numeric", PASS, "Fitted-value field is numeric.")
        complete = _complete_residual_frame(frame, fitted, residual)
    else:
        report.add(
            "data.residual.fitted.numeric",
            FAIL,
            f"Fitted-value field '{fitted}' must be numeric for residual specs.",
            field=fitted,
        )
        complete = pd.DataFrame()

    _audit_diagnostic_sample_size(report, "Residual spec", len(complete), rule_id="data.residual.sample_size")
    _audit_residual_variation(report, complete, residual)
    _audit_residual_claim_support(report, complete, fitted, residual, claim)

    zero_rule = _find_zero_rule(spec)
    if zero_rule is not None:
        report.add(
            "visual.residual.zero_reference",
            PASS,
            "Residual spec includes a zero reference line.",
        )
    else:
        report.add(
            "visual.residual.zero_reference",
            FAIL,
            "Residual spec is missing a zero reference line.",
            suggestion="Add a rule layer with y datum 0 so residual sign and centering remain interpretable.",
            field="layer",
        )


def _complete_residual_frame(
    frame: pd.DataFrame,
    fitted: str | None,
    residual: str | None,
) -> pd.DataFrame:
    required = [field for field in (fitted, residual) if field and field in frame.columns]
    if len(required) != 2:
        return frame.iloc[0:0]
    return frame.loc[frame[required].notna().all(axis=1), required].copy()


def _audit_diagnostic_sample_size(
    report: AuditReport,
    label: str,
    count: int,
    *,
    rule_id: str = "data.distribution.sample_size",
) -> None:
    if count < 5:
        report.add(
            rule_id,
            FAIL,
            f"{label} has {count} complete observation(s); diagnostics need at least 5.",
            suggestion="Provide more complete observations before interpreting the diagnostic.",
        )
    elif count < 20:
        report.add(
            rule_id,
            WARN,
            f"{label} has {count} complete observations; diagnostic pattern judgments are fragile below 20.",
            suggestion="Use more observations before making strong diagnostic claims.",
        )
    else:
        report.add(rule_id, PASS, f"{label} has {count} complete observations.")


def _audit_residual_variation(
    report: AuditReport,
    complete: pd.DataFrame,
    residual: str | None,
) -> None:
    if not residual or residual not in complete.columns or complete.empty:
        return
    if complete[residual].nunique(dropna=True) <= 1:
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


def _audit_residual_claim_support(
    report: AuditReport,
    complete: pd.DataFrame,
    fitted: str | None,
    residual: str | None,
    claim: str,
) -> None:
    if (
        complete.empty
        or len(complete) < 5
        or not fitted
        or not residual
        or fitted not in complete.columns
        or residual not in complete.columns
    ):
        return

    correlation, thirds_shift = _residual_pattern_strength(complete, fitted, residual)
    strong_pattern = correlation >= RESIDUAL_CORRELATION_WARN or thirds_shift >= RESIDUAL_THIRDS_SHIFT_WARN
    denies_pattern = _contains_any(claim, NO_PATTERN_TERMS)
    if strong_pattern:
        message = (
            f"Residuals show deterministic structure: |correlation|={correlation:.2f}, "
            f"thirds mean-shift={thirds_shift:.2f} residual standard deviations."
        )
        if denies_pattern:
            message += " The claim says there is no meaningful pattern."
        report.add(
            "claim.residual.pattern_support",
            WARN,
            message,
            suggestion="Describe the observed structure and avoid claiming random scatter or no pattern.",
            field="claim",
        )
    else:
        report.add(
            "claim.residual.pattern_support",
            PASS,
            "Residual structure stays below the deterministic correlation and thirds-shift thresholds.",
        )


def _residual_pattern_strength(
    complete: pd.DataFrame,
    fitted: str,
    residual: str,
) -> tuple[float, float]:
    ordered = complete.sort_values(fitted)
    correlation = ordered[fitted].corr(ordered[residual])
    absolute_correlation = abs(float(correlation)) if pd.notna(correlation) else 0.0

    residual_scale = float(ordered[residual].std(ddof=1)) if len(ordered) > 1 else 0.0
    if residual_scale == 0:
        return absolute_correlation, 0.0

    boundaries = (0, len(ordered) // 3, (2 * len(ordered)) // 3, len(ordered))
    means = [
        float(ordered.iloc[start:end][residual].mean())
        for start, end in zip(boundaries, boundaries[1:])
        if end > start
    ]
    thirds_shift = (max(means) - min(means)) / residual_scale if means else 0.0
    return absolute_correlation, thirds_shift


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = (text or "").lower()
    return any(term in lowered for term in terms)


def _find_view(
    spec: Mapping[str, Any],
    *,
    mark: str,
    x_field: str | None = None,
    y_field: str | None = None,
) -> Mapping[str, Any] | None:
    for view in _iter_views(spec):
        if _mark_type(view) != mark:
            continue
        if x_field and _encoding_field(_encoding(view, "x")) != x_field:
            continue
        if y_field and _encoding_field(_encoding(view, "y")) != y_field:
            continue
        return view
    return None


def _find_zero_rule(spec: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for view in _iter_views(spec):
        if _mark_type(view) != "rule":
            continue
        y_encoding = _encoding(view, "y")
        if isinstance(y_encoding, Mapping) and y_encoding.get("datum") == 0:
            return view
    return None


def _iter_views(spec: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    yield spec
    layers = spec.get("layer")
    if isinstance(layers, list):
        for layer in layers:
            if isinstance(layer, Mapping):
                yield from _iter_views(layer)


def _mark_type(spec: Mapping[str, Any]) -> str:
    mark = spec.get("mark")
    if isinstance(mark, str):
        return mark
    if isinstance(mark, Mapping):
        return str(mark.get("type", ""))
    return ""


def _encoding(spec: Mapping[str, Any] | None, channel: str) -> Any:
    if spec is None:
        return None
    encoding = spec.get("encoding")
    if not isinstance(encoding, Mapping):
        return None
    return encoding.get(channel)


def _encoding_field(encoding: Any) -> str | None:
    if isinstance(encoding, Mapping):
        field = encoding.get("field")
        return field if isinstance(field, str) and field else None
    if isinstance(encoding, str):
        field, separator, _ = encoding.rpartition(":")
        return field if separator and field else None
    return None
