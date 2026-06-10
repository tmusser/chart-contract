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


def test_audit_report_to_markdown_includes_summary_and_findings() -> None:
    df = pd.DataFrame({"week": ["2026-05-01"], "value": [0.12]})

    report = Chart.trend(data=df, x="week", y="value", claim="", unit="rate").audit()
    markdown = report.to_markdown()

    assert "# Audit Report" in markdown
    assert "Summary:" in markdown
    assert "`contract.claim.present`" in markdown


def test_audit_report_raise_on_fail_raises_for_failures() -> None:
    df = pd.DataFrame({"week": ["2026-05-01"], "value": [0.12]})

    report = Chart.trend(data=df, x="week", y="value", claim="", unit="rate").audit()

    with pytest.raises(ValueError, match="contract.claim.present"):
        report.raise_on_fail()


def test_audit_report_raise_on_fail_is_noop_without_failures() -> None:
    df = pd.DataFrame({"week": ["2026-05-01"], "value": [0.12]})

    report = Chart.trend(
        data=df,
        x="week",
        y="value",
        claim="Conversion improved",
        source="warehouse.funnel_events",
        unit="conversion rate",
    ).audit()

    report.raise_on_fail()
