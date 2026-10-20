from __future__ import annotations

from copy import deepcopy

import pandas as pd

from chart_contract import Chart, audit_spec


def _finding(report, rule_id: str):
    return next(f for f in report.findings if f.rule_id == rule_id)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "period": ["before", "after"],
            "latency_ms": [200.0, 250.0],
        }
    )


def _chart(claim: str, **overrides) -> Chart:
    kwargs = {
        "data": _frame(),
        "x": "period",
        "y": "latency_ms",
        "claim": claim,
        "source": "synthetic.latency",
        "unit": "milliseconds",
        "title": "Observed latency",
        "metric_direction": "lower_is_better",
        "baseline_field": "period",
        "baseline_value": "before",
        "target_value": "after",
        "change_type": "absolute",
        "declared_change": 50.0,
    }
    kwargs.update(overrides)
    return Chart.trend(**kwargs)


def test_lower_is_better_improvement_claim_blocks_when_metric_rises() -> None:
    report = _chart("Latency improved.").audit()

    assert _finding(report, "contract.metric.directionality").severity == "PASS"
    finding = _finding(report, "claim.metric.directionality")
    assert finding.severity == "FAIL"
    assert "worsening" in finding.message
    assert report.verdict == "BLOCK"


def test_lower_is_better_worsening_claim_passes_when_metric_rises() -> None:
    report = _chart("Latency worsened.").audit()

    finding = _finding(report, "claim.metric.directionality")
    assert finding.severity == "PASS"
    assert report.verdict == "READY"


def test_higher_is_better_improvement_claim_passes_when_metric_rises() -> None:
    report = _chart(
        "Throughput improved.",
        y="latency_ms",
        metric_direction="higher_is_better",
    ).audit()

    assert _finding(report, "claim.metric.directionality").severity == "PASS"
    assert report.verdict == "READY"


def test_neutral_metric_rejects_better_worse_claim() -> None:
    report = _chart(
        "The metric improved.",
        metric_direction="neutral",
    ).audit()

    finding = _finding(report, "claim.metric.directionality")
    assert finding.severity == "FAIL"
    assert "neutral" in finding.message
    assert report.verdict == "BLOCK"


def test_evaluative_claim_without_directionality_requires_review() -> None:
    report = _chart(
        "Latency improved.",
        metric_direction=None,
    ).audit()

    finding = _finding(report, "claim.metric.directionality")
    assert finding.severity == "WARN"
    assert report.verdict == "REVIEW"


def test_evaluative_claim_without_explicit_comparison_requires_review() -> None:
    chart = Chart.trend(
        data=_frame(),
        x="period",
        y="latency_ms",
        claim="Latency improved.",
        source="synthetic.latency",
        unit="milliseconds",
        title="Observed latency",
        metric_direction="lower_is_better",
    )

    report = chart.audit()

    assert _finding(report, "contract.metric.directionality").severity == "PASS"
    assert _finding(report, "claim.metric.directionality").severity == "WARN"
    assert report.verdict == "REVIEW"


def test_plain_increase_language_is_not_evaluative() -> None:
    report = _chart("Latency increased.").audit()

    assert _finding(report, "contract.metric.directionality").severity == "PASS"
    assert not any(
        f.rule_id == "claim.metric.directionality" for f in report.findings
    )
    assert report.verdict == "READY"


def test_unchanged_metric_rejects_improvement_claim() -> None:
    frame = pd.DataFrame(
        {
            "period": ["before", "after"],
            "latency_ms": [200.0, 200.0],
        }
    )
    chart = Chart.trend(
        data=frame,
        x="period",
        y="latency_ms",
        claim="Latency improved.",
        source="synthetic.latency",
        unit="milliseconds",
        title="Observed latency",
        metric_direction="lower_is_better",
        baseline_field="period",
        baseline_value="before",
        target_value="after",
        change_type="absolute",
        declared_change=0.0,
    )

    report = chart.audit()

    finding = _finding(report, "claim.metric.directionality")
    assert finding.severity == "FAIL"
    assert "unchanged" in finding.message


def test_first_party_spec_preserves_closed_directionality_contract() -> None:
    spec = _chart("Latency worsened.").to_vega_lite()

    assert spec["usermeta"]["directionality_contract"] == {
        "version": 1,
        "metric_field": "latency_ms",
        "direction": "lower_is_better",
    }


def _external_spec() -> tuple[dict, pd.DataFrame]:
    frame = _frame()
    spec = {
        "mark": "line",
        "title": "Observed latency",
        "encoding": {
            "x": {"field": "period", "type": "ordinal"},
            "y": {"field": "latency_ms", "type": "quantitative"},
        },
        "usermeta": {
            "source": "synthetic.latency",
            "unit": "milliseconds",
            "directionality_contract": {
                "version": 1,
                "metric_field": "latency_ms",
                "direction": "lower_is_better",
            },
            "comparison_contract": {
                "version": 1,
                "metric_field": "latency_ms",
                "baseline_field": "period",
                "baseline_value": "before",
                "target_value": "after",
                "change_type": "absolute",
                "declared_change": 50.0,
                "baseline_metric_value": 200.0,
                "target_metric_value": 250.0,
                "computed_change": 50.0,
            },
        },
    }
    return spec, frame


def test_external_directionality_mismatch_blocks() -> None:
    spec, frame = _external_spec()

    report = audit_spec(
        spec,
        data=frame,
        claim="Latency improved.",
    )

    assert _finding(report, "contract.metric.directionality").severity == "PASS"
    assert _finding(report, "claim.metric.directionality").severity == "FAIL"
    assert report.verdict == "BLOCK"


def test_external_matching_directionality_passes() -> None:
    spec, frame = _external_spec()

    report = audit_spec(
        spec,
        data=frame,
        claim="Latency worsened.",
    )

    assert _finding(report, "claim.metric.directionality").severity == "PASS"
    assert report.verdict == "READY"


def test_external_directionality_metric_binding_drift_blocks() -> None:
    spec, frame = _external_spec()
    spec["usermeta"]["directionality_contract"]["metric_field"] = "other_metric"

    report = audit_spec(
        spec,
        data=frame,
        claim="Latency worsened.",
    )

    assert _finding(report, "contract.metric.directionality").severity == "FAIL"


def test_closed_directionality_schema_blocks_extra_fields() -> None:
    spec, frame = _external_spec()
    spec["usermeta"]["directionality_contract"]["target"] = 150

    report = audit_spec(
        spec,
        data=frame,
        claim="Latency worsened.",
    )

    assert _finding(report, "contract.metric.directionality").severity == "FAIL"


def test_unsupported_direction_blocks() -> None:
    report = _chart(
        "Latency changed after launch.",
        metric_direction="minimize",
    ).audit()

    assert _finding(report, "contract.metric.directionality").severity == "FAIL"


def test_ambiguous_better_and_worse_wording_blocks() -> None:
    report = _chart(
        "Latency improved in one sense but worsened overall.",
    ).audit()

    finding = _finding(report, "claim.metric.directionality")
    assert finding.severity == "FAIL"
    assert "mixes improvement and worsening" in finding.message
