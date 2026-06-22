"""Audit models and rules."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd

from .contracts import (
    declared_caveat_from_spec,
    declared_evidence_from_spec,
    declared_source_from_spec,
    declared_unit_from_spec,
    extract_inline_values,
    find_decorative_terms,
    has_causal_language,
    has_declared_causal_evidence,
    implies_filter_or_time_window,
    is_datetime_like,
    is_generic_title,
    is_numeric_series,
    is_ordered_series,
)

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
SEVERITIES = {PASS, WARN, FAIL}
READY = "READY"
REVIEW = "REVIEW"
BLOCK = "BLOCK"
REPORT_SCHEMA_VERSION = "0.2"


@dataclass(slots=True)
class AuditFinding:
    rule_id: str
    severity: str
    message: str
    suggestion: str | None = None
    field: str | None = None

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(f"Unknown severity: {self.severity}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AuditReport:
    findings: list[AuditFinding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.has_failures

    @property
    def has_warnings(self) -> bool:
        return any(finding.severity == WARN for finding in self.findings)

    @property
    def has_failures(self) -> bool:
        return any(finding.severity == FAIL for finding in self.findings)

    @property
    def verdict(self) -> str:
        if self.has_failures:
            return BLOCK
        if self.has_warnings:
            return REVIEW
        return READY

    def summary(self) -> str:
        counts = {severity: 0 for severity in (PASS, WARN, FAIL)}
        for finding in self.findings:
            counts[finding.severity] += 1
        return f"PASS={counts[PASS]} WARN={counts[WARN]} FAIL={counts[FAIL]}"

    def verdict_summary(self) -> str:
        return f"{self.verdict}: {self.summary()}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": REPORT_SCHEMA_VERSION,
            "passed": self.passed,
            "has_failures": self.has_failures,
            "has_warnings": self.has_warnings,
            "verdict": self.verdict,
            "summary": self.summary(),
            "verdict_summary": self.verdict_summary(),
            "findings": [finding.to_dict() for finding in self.findings],
        }

    def to_markdown(self) -> str:
        lines = [
            "# Audit Report",
            "",
            f"Verdict: `{self.verdict}`",
            "",
            f"Summary: `{self.summary()}`",
            "",
            "## Findings",
            "",
        ]
        if not self.findings:
            lines.append("- None")
        else:
            for finding in self.findings:
                line = f"- **{finding.severity}** `{finding.rule_id}`: {finding.message}"
                if finding.suggestion:
                    line += f" Suggestion: {finding.suggestion}"
                lines.append(line)
        return "\n".join(lines)

    def raise_on_fail(self) -> None:
        failures = [finding for finding in self.findings if finding.severity == FAIL]
        if not failures:
            return
        failure_lines = [f"{finding.rule_id}: {finding.message}" for finding in failures]
        raise ValueError("Audit report contains failures:\n" + "\n".join(failure_lines))

    def add(
        self,
        rule_id: str,
        severity: str,
        message: str,
        suggestion: str | None = None,
        field: str | None = None,
    ) -> None:
        self.findings.append(
            AuditFinding(
                rule_id=rule_id,
                severity=severity,
                message=message,
                suggestion=suggestion,
                field=field,
            )
        )


def audit_chart(chart: Any) -> AuditReport:
    report = AuditReport()
    claim = (chart.claim or "").strip()
    title = (chart.title or claim).strip()
    source = (chart.source or "").strip()
    caveat = (chart.caveat or "").strip()

    if claim:
        report.add("contract.claim.present", PASS, "Claim is declared.")
    else:
        report.add(
            "contract.claim.present",
            FAIL,
            "Claim is required for an audited chart.",
            suggestion="Add a claim that states what the viewer should believe from the chart.",
            field="claim",
        )

    if source:
        report.add("contract.source.present", PASS, "Source is declared.")
    else:
        report.add(
            "contract.source.present",
            WARN,
            "Source is missing; provenance should be visible.",
            suggestion="Add a source such as a table, model, or query identifier.",
            field="source",
        )

    if chart.y not in chart.data.columns:
        report.add(
            "data.y.column",
            FAIL,
            f"Required y column '{chart.y}' is missing from the data.",
            field=chart.y,
        )
    elif is_numeric_series(chart.data[chart.y]):
        report.add("data.y.numeric", PASS, "Y field is quantitative.")
        if chart.unit:
            report.add("labels.unit.present", PASS, "Unit is declared for the quantitative metric.")
        else:
            report.add(
                "labels.unit.present",
                WARN,
                "Unit is missing for a quantitative metric.",
                suggestion="Add a unit such as percent, count, dollars, or rate.",
                field="unit",
            )
    else:
        report.add(
            "data.y.numeric",
            FAIL,
            f"Y field '{chart.y}' must be numeric for {chart.intent} charts.",
            field=chart.y,
        )

    required_columns = [chart.x, chart.y]
    if chart.group:
        required_columns.append(chart.group)
    for column in required_columns:
        if column not in chart.data.columns:
            report.add(
                "data.required.column",
                FAIL,
                f"Required column '{column}' is missing from the data.",
                field=column,
            )

    if chart.data.empty:
        report.add(
            "data.not_empty",
            WARN,
            "Chart data is empty; the rendered chart will not support the claim.",
        )
    else:
        report.add("data.not_empty", PASS, "Chart data is not empty.")

    if chart.intent == "trend":
        row_count = len(chart.data)
        if row_count < 2:
            report.add(
                "data.trend.min_points",
                FAIL,
                f"Trend chart has {row_count} data point(s); a directional trend claim requires at least 2.",
                suggestion="Add historical data covering at least two time periods.",
            )
        else:
            report.add(
                "data.trend.min_points",
                PASS,
                "Trend chart has enough data points to show direction.",
            )

    if chart.intent == "trend" and chart.x in chart.data.columns:
        x_series = chart.data[chart.x]
        if is_datetime_like(x_series) or is_ordered_series(x_series):
            report.add("data.trend.x.ordered", PASS, "Trend x field is ordered or datetime-like.")
        else:
            report.add(
                "data.trend.x.ordered",
                WARN,
                "Trend x field is not clearly ordered or datetime-like.",
                suggestion="Use a time field, numeric sequence, or ordered categorical series.",
                field=chart.x,
            )

    if chart.intent == "rank" and chart.x in chart.data.columns:
        category_count = chart.data[chart.x].nunique(dropna=True)
        if category_count > 12:
            report.add(
                "readability.rank.category_count",
                WARN,
                f"Rank chart has {category_count} categories, which may be hard to read.",
                suggestion="Reduce categories or aggregate a long tail before sharing.",
                field=chart.x,
            )
        else:
            report.add("readability.rank.category_count", PASS, "Rank chart category count is readable.")

    if chart.group and chart.group in chart.data.columns:
        group_count = chart.data[chart.group].nunique(dropna=True)
        if group_count > 8:
            report.add(
                "readability.color.category_count",
                WARN,
                f"Color encoding uses {group_count} groups, which may distract from the metric.",
                suggestion="Reduce groups or facet the comparison.",
                field=chart.group,
            )
        else:
            report.add("readability.color.category_count", PASS, "Color encoding category count is readable.")

    if has_causal_language(claim) and not (caveat or has_declared_causal_evidence(chart.metadata)):
        report.add(
            "claim.causal_support",
            WARN,
            "Claim uses causal language without a caveat or causal evidence flag.",
            suggestion="Add a caveat or set metadata['causal_evidence']=True when the evidence supports it.",
            field="claim",
        )
    elif claim:
        report.add("claim.causal_support", PASS, "Claim support language is acceptable for v0.1.")

    if chart.event and not caveat:
        report.add(
            "claim.event_without_caveat",
            WARN,
            "Event annotation is present without a caveat; viewers may infer causality from timing alone.",
            suggestion="Add a caveat clarifying whether the event is descriptive or causal.",
            field="event",
        )

    if claim and implies_filter_or_time_window(claim) and not chart.filters:
        report.add(
            "contract.filters.implied",
            WARN,
            "Claim implies a filter or time window that is not explicitly declared.",
            suggestion="Add filters metadata or clarify the time window in the chart contract.",
            field="filters",
        )

    if is_generic_title(title):
        report.add(
            "labels.title.quality",
            WARN,
            "Chart title is missing or generic.",
            suggestion="Use a specific title or a concrete analytical claim.",
            field="title",
        )
    else:
        report.add("labels.title.quality", PASS, "Title is specific enough to support interpretation.")

    report.add(
        "visual.intent.match",
        PASS,
        f"{chart.intent.title()} visual form matches the declared chart intent.",
    )

    decorative_terms = find_decorative_terms(chart.metadata or {})
    if decorative_terms:
        report.add(
            "visual.integrity.decoration",
            WARN,
            f"Decorative metadata hints at distracting encodings: {', '.join(decorative_terms)}.",
            suggestion="Prefer data-ink over decorative effects.",
        )
    else:
        report.add(
            "visual.integrity.decoration",
            PASS,
            "No decorative metadata suggests chartjunk-like encodings.",
        )

    return report


def audit_spec(
    spec: Mapping[str, Any],
    data: pd.DataFrame | Sequence[Mapping[str, Any]] | None = None,
    claim: str | None = None,
) -> AuditReport:
    """Audit a Vega-Lite-like specification.

    This is an experimental helper for checking risky specs before sharing them.
    """

    report = AuditReport()
    mark = _mark_type(spec)
    encoding = spec.get("encoding", {})
    x_encoding = encoding.get("x", {}) if isinstance(encoding, Mapping) else {}
    y_encoding = encoding.get("y", {}) if isinstance(encoding, Mapping) else {}
    color_encoding = encoding.get("color", {}) if isinstance(encoding, Mapping) else {}
    title = _title_text(spec.get("title"))
    source = declared_source_from_spec(spec)
    unit = declared_unit_from_spec(spec)
    caveat = declared_caveat_from_spec(spec)
    evidence_flag = declared_evidence_from_spec(spec)
    resolved_claim = (claim or "").strip()
    resolved_data = _coerce_records(spec, data)

    if resolved_claim:
        report.add("contract.claim.present", PASS, "Claim is declared for the spec audit.")
    else:
        report.add(
            "contract.claim.present",
            FAIL,
            "Spec audit needs a claim to evaluate support and caveats.",
            suggestion="Pass claim=... when calling audit_spec().",
            field="claim",
        )

    if source:
        report.add("contract.source.present", PASS, "Source is declared in spec user metadata.")
    else:
        report.add(
            "contract.source.present",
            WARN,
            "Spec is missing source/provenance metadata.",
            suggestion="Add spec['usermeta']['source'] to preserve provenance.",
            field="source",
        )

    if _has_quantitative_axis(x_encoding) or _has_quantitative_axis(y_encoding):
        if unit:
            report.add("labels.unit.present", PASS, "Spec declares a unit for a quantitative field.")
        else:
            report.add(
                "labels.unit.present",
                WARN,
                "Spec is missing a unit for a quantitative field.",
                suggestion="Add spec['usermeta']['unit'] or a clear axis title with units.",
                field="unit",
            )

    if is_generic_title(title):
        report.add(
            "labels.title.quality",
            WARN,
            "Spec title is missing or generic.",
            suggestion="Use a specific title tied to the claim.",
            field="title",
        )
    else:
        report.add("labels.title.quality", PASS, "Spec title is specific enough.")

    if has_causal_language(resolved_claim) and not (caveat or evidence_flag):
        report.add(
            "claim.causal_support",
            WARN,
            "Claim uses causal language without a caveat or causal evidence metadata.",
            suggestion="Add a caveat or spec['usermeta']['causal_evidence']=True when justified.",
            field="claim",
        )
    elif resolved_claim:
        report.add("claim.causal_support", PASS, "Claim support language is acceptable for the audited spec.")

    if mark == "line" and x_encoding and y_encoding and resolved_data is not None:
        row_count = len(resolved_data)
        if row_count < 2:
            report.add(
                "data.trend.min_points",
                FAIL,
                f"Trend spec has {row_count} data point(s) and needs at least 2.",
                suggestion="Add historical data covering at least two time periods.",
            )
        else:
            report.add(
                "data.trend.min_points",
                PASS,
                "Trend spec has enough data points to show direction.",
            )

    if mark == "bar":
        if _quantitative_axis_uses_nonzero_baseline(x_encoding):
            report.add(
                "scale.bar.nonzero_baseline",
                FAIL,
                "Bar chart uses a quantitative x-axis with zero baseline disabled.",
                suggestion="Set scale.zero=true for bar chart quantitative axes.",
                field="encoding.x.scale.zero",
            )
        elif _quantitative_axis_uses_nonzero_baseline(y_encoding):
            report.add(
                "scale.bar.nonzero_baseline",
                FAIL,
                "Bar chart uses a quantitative y-axis with zero baseline disabled.",
                suggestion="Set scale.zero=true for bar chart quantitative axes.",
                field="encoding.y.scale.zero",
            )
        else:
            report.add("scale.bar.nonzero_baseline", PASS, "Bar chart baseline behavior is acceptable.")

    if mark == "arc":
        category_count = _category_count(resolved_data, color_encoding)
        if category_count is not None and category_count > 6:
            report.add(
                "visual.arc.category_count",
                FAIL,
                f"Pie/arc chart uses {category_count} categories; use a sorted bar chart instead.",
                suggestion="Switch to a rank chart with bars for easier comparisons.",
                field="encoding.color",
            )
        elif category_count is not None:
            report.add("visual.arc.category_count", PASS, "Pie/arc category count is within the v0.1 limit.")

    color_count = _category_count(resolved_data, color_encoding)
    if color_count is not None and color_count > 8:
        report.add(
            "readability.color.category_count",
            WARN,
            f"Color encoding uses {color_count} categories, which may reduce readability.",
            suggestion="Reduce categories or facet the view.",
            field="encoding.color",
        )
    elif color_count is not None:
        report.add("readability.color.category_count", PASS, "Color encoding category count is readable.")

    decorative_terms = find_decorative_terms(spec)
    if decorative_terms:
        report.add(
            "visual.integrity.decoration",
            FAIL if mark == "arc" else WARN,
            f"Spec contains decorative or depth-like elements: {', '.join(decorative_terms)}.",
            suggestion="Remove decorative fields and prefer plain analytical encodings.",
        )
    else:
        report.add("visual.integrity.decoration", PASS, "No decorative chartjunk-like spec fields detected.")

    return report


def _mark_type(spec: Mapping[str, Any]) -> str:
    mark = spec.get("mark")
    if isinstance(mark, str):
        return mark
    if isinstance(mark, Mapping):
        return str(mark.get("type", ""))
    return ""


def _title_text(title: Any) -> str:
    if isinstance(title, str):
        return title
    if isinstance(title, Mapping):
        text = title.get("text")
        if isinstance(text, str):
            return text
    return ""


def _has_quantitative_axis(encoding: Any) -> bool:
    return isinstance(encoding, Mapping) and encoding.get("type") == "quantitative"


def _quantitative_axis_uses_nonzero_baseline(encoding: Any) -> bool:
    if not _has_quantitative_axis(encoding):
        return False
    scale = encoding.get("scale", {})
    return isinstance(scale, Mapping) and scale.get("zero") is False


def _coerce_records(
    spec: Mapping[str, Any],
    data: pd.DataFrame | Sequence[Mapping[str, Any]] | None,
) -> list[dict[str, Any]] | None:
    if isinstance(data, pd.DataFrame):
        return data.to_dict(orient="records")
    if data is not None:
        return [dict(item) for item in data]
    return extract_inline_values(spec)


def _category_count(records: list[dict[str, Any]] | None, encoding: Any) -> int | None:
    if not records or not isinstance(encoding, Mapping):
        return None
    field = encoding.get("field")
    if not isinstance(field, str):
        return None
    values = {record.get(field) for record in records if field in record}
    return len(values)
