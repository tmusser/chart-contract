"""Audit models and rules."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
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
DISTRIBUTION_INTENTS = {"histogram", "boxplot", "violin"}
SUPPORTED_CHART_INTENTS = {"trend", "rank", "compare", *DISTRIBUTION_INTENTS}
ENCODING_TYPE_CODES = {
    "Q": "quantitative",
    "N": "nominal",
    "O": "ordinal",
    "T": "temporal",
    "G": "geojson",
}


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
    distribution_intent = chart.intent in DISTRIBUTION_INTENTS
    metric_field = _chart_metric_field(chart)
    category_field = _distribution_category_field(chart)

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

    if distribution_intent:
        _audit_distribution_value(report, chart, metric_field)
    else:
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

    required_columns = _required_fields_for_chart(chart)
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

    if distribution_intent:
        _audit_distribution_sample_size(report, chart, category_field, metric_field)
        if chart.intent == "histogram":
            _audit_histogram_bins(report, chart)
        if chart.intent == "violin":
            _audit_violin_sample_size(report, chart, metric_field)

    if chart.intent == "trend":
        point_count = _complete_observation_count(chart.data, (chart.x, chart.y))
        if point_count < 2:
            report.add(
                "data.trend.min_points",
                FAIL,
                f"Trend chart has {point_count} complete data point(s); a directional trend claim requires at least 2.",
                suggestion="Add at least two observations with non-null x and y values.",
            )
        else:
            report.add(
                "data.trend.min_points",
                PASS,
                "Trend chart has at least two complete data points to show direction.",
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

    if chart.intent in SUPPORTED_CHART_INTENTS:
        report.add(
            "visual.intent.match",
            PASS,
            f"{chart.intent.title()} visual form matches the declared chart intent.",
        )
    else:
        report.add(
            "visual.intent.match",
            FAIL,
            f"Unsupported chart intent: {chart.intent!r}.",
            suggestion="Use one of the supported Chart constructors instead of setting intent directly.",
            field="intent",
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
    analytical_spec = _primary_analytical_spec(spec)
    mark = _mark_type(analytical_spec)
    encoding = analytical_spec.get("encoding", {})
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
    resolved_frame = pd.DataFrame(resolved_data) if resolved_data is not None else None

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

    if _has_quantitative_encoding(encoding):
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

    _audit_spec_encoding_fields(report, encoding, resolved_frame)

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

    if mark == "line" and x_encoding and y_encoding and resolved_frame is not None:
        x_field = _encoding_field(x_encoding)
        y_field = _encoding_field(y_encoding)
        if x_field and y_field:
            point_count = _complete_observation_count(resolved_frame, (x_field, y_field))
        else:
            point_count = len(resolved_frame)
        if point_count < 2:
            report.add(
                "data.trend.min_points",
                FAIL,
                f"Trend spec has {point_count} complete data point(s) and needs at least 2.",
                suggestion="Add at least two observations with non-null x and y values.",
            )
        else:
            report.add(
                "data.trend.min_points",
                PASS,
                "Trend spec has at least two complete data points to show direction.",
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

    distribution_kind = _distribution_spec_kind(mark, spec, x_encoding, y_encoding, color_encoding)
    if distribution_kind and resolved_frame is not None:
        _audit_distribution_spec(
            report,
            distribution_kind,
            resolved_frame,
            x_encoding,
            y_encoding,
            color_encoding,
        )

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

    from .statistical_audit import audit_statistical_spec

    audit_statistical_spec(report, spec, resolved_frame, resolved_claim)

    return report


def _primary_analytical_spec(spec: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the first data-bearing analytical view from a layered spec."""
    if _mark_type(spec) and isinstance(spec.get("encoding"), Mapping):
        return spec

    layers = spec.get("layer")
    if isinstance(layers, list):
        for layer in layers:
            if not isinstance(layer, Mapping):
                continue
            mark = _mark_type(layer)
            encoding = layer.get("encoding")
            if mark in {"line", "bar", "arc", "area", "boxplot", "point"} and isinstance(encoding, Mapping):
                return layer
            nested = _primary_analytical_spec(layer)
            if nested is not layer and _mark_type(nested):
                return nested

    return spec


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
    return _encoding_type(encoding) == "quantitative"


def _has_quantitative_encoding(encoding: Any) -> bool:
    if not isinstance(encoding, Mapping):
        return False
    return any(_has_quantitative_axis(item) for _, item in _iter_encoding_definitions(encoding))


def _quantitative_axis_uses_nonzero_baseline(encoding: Any) -> bool:
    if not _has_quantitative_axis(encoding) or not isinstance(encoding, Mapping):
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


def _audit_spec_encoding_fields(report: AuditReport, encoding: Any, frame: pd.DataFrame | None) -> None:
    if frame is None or not isinstance(encoding, Mapping):
        return

    encoded_fields: set[str] = set()
    quantitative_fields: set[str] = set()
    for _, definition in _iter_encoding_definitions(encoding):
        field = _encoding_field(definition)
        if not field:
            continue
        encoded_fields.add(field)
        if _encoding_type(definition) == "quantitative":
            quantitative_fields.add(field)

    if not encoded_fields:
        return

    missing_fields = sorted(field for field in encoded_fields if field not in frame.columns)
    if missing_fields:
        report.add(
            "data.encoding.fields",
            FAIL,
            f"Encoded field(s) are missing from the data: {', '.join(missing_fields)}.",
            suggestion="Add the missing columns or update the spec encodings.",
            field=missing_fields[0],
        )
    else:
        report.add("data.encoding.fields", PASS, "All encoded fields are present in the data.")

    non_numeric = sorted(
        field
        for field in quantitative_fields
        if field in frame.columns and not is_numeric_series(frame[field])
    )
    if non_numeric:
        report.add(
            "data.encoding.quantitative",
            FAIL,
            f"Quantitative encoded field(s) are not numeric: {', '.join(non_numeric)}.",
            suggestion="Convert quantitative fields to numeric data or change their encoding type.",
            field=non_numeric[0],
        )
    elif quantitative_fields and not missing_fields:
        report.add(
            "data.encoding.quantitative",
            PASS,
            "Quantitative encoded fields are numeric.",
        )


def _iter_encoding_definitions(encoding: Mapping[str, Any]) -> Iterator[tuple[str, Any]]:
    for channel, definition in encoding.items():
        if isinstance(definition, list):
            for item in definition:
                yield channel, item
        else:
            yield channel, definition


def _category_count(records: list[dict[str, Any]] | None, encoding: Any) -> int | None:
    if not records:
        return None
    field = _encoding_field(encoding)
    if not field:
        return None
    values = {record.get(field) for record in records if field in record}
    return len(values)


def _distribution_spec_kind(
    mark: str,
    spec: Mapping[str, Any],
    x_encoding: Any,
    y_encoding: Any,
    color_encoding: Any,
) -> str | None:
    if mark == "bar" and _encoding_bin_config(x_encoding) is not None and _encoding_aggregate(y_encoding) == "count":
        return "histogram"
    if mark == "boxplot":
        return "boxplot"
    if mark == "area" and _contains_density_transform(spec):
        return "violin"
    return None


def _audit_distribution_spec(
    report: AuditReport,
    kind: str,
    resolved_frame: pd.DataFrame,
    x_encoding: Any,
    y_encoding: Any,
    color_encoding: Any,
) -> None:
    metric_field = _distribution_spec_metric_field(kind, x_encoding, y_encoding)
    if not metric_field:
        report.add(
            "data.distribution.value.numeric",
            FAIL,
            f"{kind.title()} specs require a metric field.",
            suggestion="Add a numeric metric field to the distribution spec.",
        )
    elif metric_field not in resolved_frame.columns:
        report.add(
            "data.distribution.value.numeric",
            FAIL,
            f"Distribution value field '{metric_field}' is missing from the data.",
            suggestion="Add the metric column or change the chart to use an existing field.",
            field=metric_field,
        )
    elif is_numeric_series(resolved_frame[metric_field]):
        report.add(
            "data.distribution.value.numeric",
            PASS,
            "Distribution value field is numeric.",
        )
    else:
        report.add(
            "data.distribution.value.numeric",
            FAIL,
            f"Distribution value field '{metric_field}' must be numeric for {kind} specs.",
            field=metric_field,
        )

    valid_frame = _valid_metric_frame(resolved_frame, metric_field)
    row_count = len(valid_frame)
    if row_count < 5:
        report.add(
            "data.distribution.sample_size",
            FAIL,
            f"{kind.title()} spec has {row_count} observation(s); distribution shape and summary claims need enough observations.",
            suggestion="Collect more observations before summarizing the distribution.",
        )
    elif row_count < 20:
        report.add(
            "data.distribution.sample_size",
            WARN,
            f"{kind.title()} spec has {row_count} observation(s); distribution shape and summary claims need more data.",
            suggestion="Use more observations before making shape or summary claims.",
        )
    else:
        report.add(
            "data.distribution.sample_size",
            PASS,
            f"{kind.title()} spec has {row_count} observations.",
        )

    category_field = _distribution_spec_category_field(kind, x_encoding, color_encoding)
    if category_field and category_field in valid_frame.columns:
        group_counts = valid_frame[category_field].dropna().value_counts()
        if not group_counts.empty:
            if (group_counts < 10).any():
                smallest = int(group_counts.min())
                report.add(
                    "data.distribution.group_sample_size",
                    WARN,
                    f"Distribution groups in '{category_field}' include categories with fewer than 10 rows; the smallest group has {smallest}.",
                    suggestion="Aggregate small groups or collect more data for each group.",
                    field=category_field,
                )
            else:
                report.add(
                    "data.distribution.group_sample_size",
                    PASS,
                    f"All non-null groups in '{category_field}' have at least 10 rows.",
                )

    if kind == "histogram":
        _audit_histogram_spec_bins(report, x_encoding)
    if kind == "violin" and row_count < 30:
        report.add(
            "visual.violin.sample_size",
            WARN,
            f"Violin spec has {row_count} observation(s); boxplot or point summary is safer for small samples.",
            suggestion="Use a boxplot or strip/point summary when the sample is small.",
        )
    elif kind == "violin":
        report.add(
            "visual.violin.sample_size",
            PASS,
            f"Violin spec has {row_count} observations.",
        )


def _distribution_spec_metric_field(kind: str, x_encoding: Any, y_encoding: Any) -> str | None:
    if kind == "histogram":
        return _encoding_field(x_encoding)
    if kind in {"boxplot", "violin"}:
        return _encoding_field(y_encoding)
    return None


def _distribution_spec_category_field(kind: str, x_encoding: Any, color_encoding: Any) -> str | None:
    if kind == "histogram":
        return _encoding_field(color_encoding)
    if kind == "boxplot":
        return _encoding_field(x_encoding)
    if kind == "violin":
        return _encoding_field(color_encoding)
    return None


def _audit_histogram_spec_bins(report: AuditReport, x_encoding: Any) -> None:
    bin_config = _encoding_bin_config(x_encoding)
    if bin_config is None or bin_config is True:
        report.add(
            "readability.histogram.bins",
            PASS,
            "Histogram uses default binning.",
        )
        return
    if isinstance(bin_config, Mapping):
        maxbins = bin_config.get("maxbins")
        if isinstance(maxbins, int) and 5 <= maxbins <= 50:
            report.add(
                "readability.histogram.bins",
                PASS,
                f"Histogram uses {maxbins} bins, which is a readable range.",
            )
        elif isinstance(maxbins, int):
            report.add(
                "readability.histogram.bins",
                WARN,
                f"Histogram uses {maxbins} bins, which may be too coarse or too fine for quick reading.",
                suggestion="Use a bin count between 5 and 50 unless the claim needs a custom setting.",
                field="encoding.x.bin.maxbins",
            )
        else:
            report.add(
                "readability.histogram.bins",
                PASS,
                "Histogram binning is user-controlled.",
            )
        return
    report.add(
        "readability.histogram.bins",
        PASS,
        "Histogram binning is user-controlled.",
    )


def _encoding_field(encoding: Any) -> str | None:
    if isinstance(encoding, Mapping):
        field = encoding.get("field")
        if isinstance(field, str) and field:
            return field
    shorthand = _encoding_shorthand(encoding)
    return shorthand[0] if shorthand else None


def _encoding_type(encoding: Any) -> str | None:
    if isinstance(encoding, Mapping):
        encoding_type = encoding.get("type")
        if isinstance(encoding_type, str) and encoding_type:
            return ENCODING_TYPE_CODES.get(encoding_type.upper(), encoding_type.lower())
    shorthand = _encoding_shorthand(encoding)
    return shorthand[1] if shorthand else None


def _encoding_shorthand(encoding: Any) -> tuple[str | None, str | None, str | None] | None:
    if not isinstance(encoding, str):
        return None
    expression, separator, type_code = encoding.rpartition(":")
    if not separator or not expression:
        return None
    encoding_type = ENCODING_TYPE_CODES.get(type_code.upper())
    if not encoding_type:
        return None
    aggregate = None
    field = expression
    if expression.endswith(")") and "(" in expression:
        aggregate, _, argument = expression[:-1].partition("(")
        field = argument or None
    return field, encoding_type, aggregate or None


def _encoding_bin_config(encoding: Any) -> Any:
    if isinstance(encoding, Mapping):
        return encoding.get("bin")
    return None


def _encoding_aggregate(encoding: Any) -> str | None:
    if isinstance(encoding, Mapping):
        aggregate = encoding.get("aggregate")
        if isinstance(aggregate, str) and aggregate:
            return aggregate
    shorthand = _encoding_shorthand(encoding)
    return shorthand[2] if shorthand else None


def _contains_density_transform(payload: Any) -> bool:
    if isinstance(payload, Mapping):
        if "density" in payload:
            return True
        return any(_contains_density_transform(value) for value in payload.values())
    if isinstance(payload, list):
        return any(_contains_density_transform(item) for item in payload)
    return False


def _complete_observation_count(frame: pd.DataFrame, fields: Sequence[str | None]) -> int:
    required = [field for field in fields if isinstance(field, str) and field]
    if not required or any(field not in frame.columns for field in required):
        return 0
    return int(frame[required].notna().all(axis=1).sum())


def _valid_metric_frame(frame: pd.DataFrame, metric_field: str | None) -> pd.DataFrame:
    if not metric_field or metric_field not in frame.columns:
        return frame.iloc[0:0]
    metric = frame[metric_field]
    if not is_numeric_series(metric):
        return frame.iloc[0:0]
    return frame.loc[metric.notna()]


def _chart_metric_field(chart: Any) -> str | None:
    if chart.intent == "histogram":
        return chart.value
    return chart.y


def _distribution_category_field(chart: Any) -> str | None:
    for field in (getattr(chart, "category", None), getattr(chart, "x", None), getattr(chart, "group", None)):
        if isinstance(field, str) and field:
            return field
    return None


def _required_fields_for_chart(chart: Any) -> list[str]:
    if chart.intent in DISTRIBUTION_INTENTS:
        fields: list[str] = []
        metric_field = _chart_metric_field(chart)
        if metric_field:
            fields.append(metric_field)
        category_field = _distribution_category_field(chart)
        if category_field and category_field not in fields:
            fields.append(category_field)
        group_field = getattr(chart, "group", None)
        if isinstance(group_field, str) and group_field and group_field not in fields and group_field != category_field:
            fields.append(group_field)
        return fields

    fields = []
    if getattr(chart, "x", None):
        fields.append(chart.x)
    if getattr(chart, "y", None):
        fields.append(chart.y)
    if getattr(chart, "group", None):
        fields.append(chart.group)
    return fields


def _audit_distribution_value(report: AuditReport, chart: Any, metric_field: str | None) -> None:
    if not metric_field:
        report.add(
            "data.distribution.value.numeric",
            FAIL,
            f"{chart.intent.title()} charts require a value field.",
            suggestion="Add a numeric metric column for the distribution view.",
        )
        return

    if metric_field not in chart.data.columns:
        report.add(
            "data.distribution.value.numeric",
            FAIL,
            f"Distribution value field '{metric_field}' is missing from the data.",
            suggestion="Add the metric column or change the chart to use an existing field.",
            field=metric_field,
        )
        return

    if is_numeric_series(chart.data[metric_field]):
        report.add(
            "data.distribution.value.numeric",
            PASS,
            "Distribution value field is numeric.",
        )
        if chart.unit:
            report.add("labels.unit.present", PASS, "Unit is declared for the distribution metric.")
        else:
            report.add(
                "labels.unit.present",
                WARN,
                "Unit is missing for a distribution metric.",
                suggestion="Add a unit such as percent, count, dollars, or rate.",
                field="unit",
            )
        return

    report.add(
        "data.distribution.value.numeric",
        FAIL,
        f"Distribution value field '{metric_field}' must be numeric for {chart.intent} charts.",
        field=metric_field,
    )


def _audit_distribution_sample_size(
    report: AuditReport,
    chart: Any,
    category_field: str | None,
    metric_field: str | None,
) -> None:
    valid_frame = _valid_metric_frame(chart.data, metric_field)
    row_count = len(valid_frame)
    if row_count < 5:
        report.add(
            "data.distribution.sample_size",
            FAIL,
            f"{chart.intent.title()} chart has {row_count} observation(s); distribution shape and summary claims need enough observations.",
            suggestion="Collect more observations before summarizing the distribution.",
        )
    elif row_count < 20:
        report.add(
            "data.distribution.sample_size",
            WARN,
            f"{chart.intent.title()} chart has {row_count} observation(s); distribution shape and summary claims need more data.",
            suggestion="Use more observations before making shape or summary claims.",
        )
    else:
        report.add(
            "data.distribution.sample_size",
            PASS,
            f"{chart.intent.title()} chart has {row_count} observations.",
        )

    if not category_field or category_field not in valid_frame.columns:
        return

    group_counts = valid_frame[category_field].dropna().value_counts()
    if group_counts.empty:
        return

    if (group_counts < 10).any():
        smallest = int(group_counts.min())
        report.add(
            "data.distribution.group_sample_size",
            WARN,
            f"Distribution groups in '{category_field}' include categories with fewer than 10 rows; the smallest group has {smallest}.",
            suggestion="Aggregate small groups or collect more data for each group.",
            field=category_field,
        )
    else:
        report.add(
            "data.distribution.group_sample_size",
            PASS,
            f"All non-null groups in '{category_field}' have at least 10 rows.",
        )


def _audit_histogram_bins(report: AuditReport, chart: Any) -> None:
    bins = chart.bins
    if bins is None:
        report.add(
            "readability.histogram.bins",
            PASS,
            "Histogram uses default binning.",
        )
        return
    if isinstance(bins, str):
        report.add(
            "readability.histogram.bins",
            PASS,
            "Histogram binning is user-controlled.",
        )
        return
    if isinstance(bins, int) and 5 <= bins <= 50:
        report.add(
            "readability.histogram.bins",
            PASS,
            f"Histogram uses {bins} bins, which is a readable range.",
        )
        return
    if isinstance(bins, int):
        report.add(
            "readability.histogram.bins",
            WARN,
            f"Histogram uses {bins} bins, which may be too coarse or too fine for quick reading.",
            suggestion="Use a bin count between 5 and 50 unless the claim needs a custom setting.",
            field="bins",
        )
        return

    report.add(
        "readability.histogram.bins",
        PASS,
        "Histogram binning is user-controlled.",
    )


def _audit_violin_sample_size(report: AuditReport, chart: Any, metric_field: str | None) -> None:
    row_count = len(_valid_metric_frame(chart.data, metric_field))
    if row_count < 30:
        report.add(
            "visual.violin.sample_size",
            WARN,
            f"Violin chart has {row_count} observation(s); boxplot or point summary is safer for small samples.",
            suggestion="Use a boxplot or strip/point summary when the sample is small.",
        )
    else:
        report.add(
            "visual.violin.sample_size",
            PASS,
            f"Violin chart has {row_count} observations.",
        )
