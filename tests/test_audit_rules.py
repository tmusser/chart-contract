import pandas as pd
import pytest

from chart_contract import Chart


def test_missing_claim_fails() -> None:
    df = pd.DataFrame({"week": ["2026-05-01"], "value": [0.12]})

    report = Chart.trend(data=df, x="week", y="value", claim="", unit="rate").audit()

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert severities["contract.claim.present"] == "FAIL"


def test_missing_source_warns() -> None:
    df = pd.DataFrame({"week": ["2026-05-01"], "value": [0.12]})

    report = Chart.trend(data=df, x="week", y="value", claim="Conversion improved", unit="rate").audit()

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert severities["contract.source.present"] == "WARN"


def test_missing_unit_warns_for_quantitative_y() -> None:
    df = pd.DataFrame({"week": ["2026-05-01"], "value": [0.12]})

    report = Chart.trend(
        data=df,
        x="week",
        y="value",
        claim="Conversion improved",
        source="warehouse.funnel_events",
    ).audit()

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert severities["labels.unit.present"] == "WARN"


def test_causal_language_without_caveat_warns() -> None:
    df = pd.DataFrame({"week": ["2026-05-01"], "value": [0.12]})

    report = Chart.trend(
        data=df,
        x="week",
        y="value",
        claim="The onboarding launch caused conversion to improve.",
        source="warehouse.funnel_events",
        unit="conversion rate",
    ).audit()

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert severities["claim.causal_support"] == "WARN"


def test_single_point_trend_fails() -> None:
    df = pd.DataFrame({"week": ["2026-05-01"], "value": [0.14]})

    report = Chart.trend(
        data=df,
        x="week",
        y="value",
        claim="Conversion improved steadily.",
        source="warehouse.funnel",
        unit="rate",
    ).audit()

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert severities["data.trend.min_points"] == "FAIL"
    assert report.passed is False


def test_multi_point_trend_passes_min_points() -> None:
    df = pd.DataFrame({"week": ["2026-05-01", "2026-05-08"], "value": [0.14, 0.16]})

    report = Chart.trend(
        data=df,
        x="week",
        y="value",
        claim="Conversion improved steadily.",
        source="warehouse.funnel",
        unit="rate",
    ).audit()

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert severities["data.trend.min_points"] == "PASS"


def test_audit_report_to_markdown_includes_summary_and_findings() -> None:
    df = pd.DataFrame({"week": ["2026-05-01"], "value": [0.12]})

    report = Chart.trend(data=df, x="week", y="value", claim="", unit="rate").audit()
    markdown = report.to_markdown()

    assert "# Audit Report" in markdown
    assert "Verdict:" in markdown
    assert "Summary:" in markdown
    assert "`contract.claim.present`" in markdown


def test_audit_report_raise_on_fail_raises_for_failures() -> None:
    df = pd.DataFrame({"week": ["2026-05-01"], "value": [0.12]})

    report = Chart.trend(data=df, x="week", y="value", claim="", unit="rate").audit()

    with pytest.raises(ValueError, match="contract.claim.present"):
        report.raise_on_fail()


def test_audit_report_raise_on_fail_is_noop_without_failures() -> None:
    df = pd.DataFrame({"week": ["2026-05-01", "2026-05-08"], "value": [0.12, 0.15]})

    report = Chart.trend(
        data=df,
        x="week",
        y="value",
        claim="Conversion improved",
        source="warehouse.funnel_events",
        unit="conversion rate",
    ).audit()

    severities = {finding.rule_id: finding.severity for finding in report.findings}
    assert severities["data.trend.min_points"] == "PASS"

    report.raise_on_fail()


def test_audit_report_verdict_ready_for_pass_only_report() -> None:
    df = pd.DataFrame({"week": ["2026-05-01", "2026-05-08"], "value": [0.12, 0.15]})

    report = Chart.trend(
        data=df,
        x="week",
        y="value",
        claim="Conversion improved",
        source="warehouse.funnel_events",
        unit="conversion rate",
        title="Weekly conversion rate improved",
    ).audit()

    assert report.verdict == "READY"
    assert report.verdict_summary() == f"READY: {report.summary()}"
    assert report.to_dict()["verdict"] == "READY"


def test_audit_report_verdict_review_for_warning_only_report() -> None:
    df = pd.DataFrame({"week": ["2026-05-01", "2026-05-08"], "value": [0.12, 0.15]})

    report = Chart.trend(
        data=df,
        x="week",
        y="value",
        claim="Conversion improved",
        unit="conversion rate",
        title="Weekly conversion rate improved",
    ).audit()

    assert report.verdict == "REVIEW"
    assert report.has_failures is False
    assert report.has_warnings is True


def test_audit_report_verdict_block_for_failure_report() -> None:
    df = pd.DataFrame({"week": ["2026-05-01"], "value": [0.12]})

    report = Chart.trend(
        data=df,
        x="week",
        y="value",
        claim="Conversion improved steadily.",
        source="warehouse.funnel",
        unit="rate",
        title="Weekly conversion improved steadily",
    ).audit()

    assert report.verdict == "BLOCK"
    assert report.verdict_summary() == f"BLOCK: {report.summary()}"
    assert report.to_dict()["verdict_summary"] == report.verdict_summary()
