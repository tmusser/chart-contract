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
            "conversion_rate": [0.72, 0.81],
        }
    )


def _chart(claim: str, **overrides) -> Chart:
    kwargs = {
        "data": _frame(),
        "x": "period",
        "y": "conversion_rate",
        "claim": claim,
        "source": "synthetic.targets",
        "unit": "score",
        "title": "Observed conversion rate",
        "metric_target": 0.80,
        "target_operator": "at_least",
        "target_selector_field": "period",
        "target_selector_value": "after",
        "target_tolerance": 0.0,
    }
    kwargs.update(overrides)
    return Chart.trend(**kwargs)


def test_target_met_claim_passes() -> None:
    report = _chart("Conversion met target.").audit()

    assert _finding(report, "contract.metric.target").severity == "PASS"
    finding = _finding(report, "data.metric.target_observation")
    assert finding.severity == "PASS"
    assert "target_met=True" in finding.message
    assert _finding(report, "claim.metric.target_semantics").severity == "PASS"
    assert report.verdict == "READY"


def test_target_missed_claim_blocks_when_threshold_is_met() -> None:
    report = _chart("Conversion missed target.").audit()

    finding = _finding(report, "claim.metric.target_semantics")
    assert finding.severity == "FAIL"
    assert report.verdict == "BLOCK"


def test_missing_target_contract_with_explicit_target_claim_requires_review() -> None:
    chart = Chart.trend(
        data=_frame(),
        x="period",
        y="conversion_rate",
        claim="Conversion met target.",
        source="synthetic.targets",
        unit="rate",
        title="Observed conversion rate",
    )

    report = chart.audit()

    assert _finding(report, "claim.metric.target_semantics").severity == "WARN"
    assert report.verdict == "REVIEW"


def test_at_most_target_semantics() -> None:
    frame = pd.DataFrame(
        {"period": ["before", "now"], "latency_ms": [205.0, 195.0]}
    )
    chart = Chart.trend(
        data=frame,
        x="period",
        y="latency_ms",
        claim="Latency met target.",
        source="synthetic.targets",
        unit="milliseconds",
        title="Observed latency",
        metric_target=200.0,
        target_operator="at_most",
        target_selector_field="period",
        target_selector_value="now",
    )

    report = chart.audit()

    assert _finding(report, "claim.metric.target_semantics").severity == "PASS"
    assert report.verdict == "READY"


def test_equal_target_uses_absolute_tolerance() -> None:
    frame = pd.DataFrame(
        {"period": ["before", "now"], "score": [100.2, 99.95]}
    )
    chart = Chart.trend(
        data=frame,
        x="period",
        y="score",
        claim="Score met target.",
        source="synthetic.targets",
        unit="points",
        title="Observed score",
        metric_target=100.0,
        target_operator="equal",
        target_selector_field="period",
        target_selector_value="now",
        target_tolerance=0.1,
    )

    report = chart.audit()

    assert _finding(report, "claim.metric.target_semantics").severity == "PASS"
    assert report.verdict == "READY"


def test_selector_must_resolve_to_exactly_one_observation() -> None:
    frame = pd.DataFrame(
        {
            "period": ["after", "after"],
            "conversion_rate": [0.80, 0.81],
        }
    )
    report = _chart("Conversion met target.", data=frame).audit()

    assert _finding(report, "contract.metric.target").severity == "PASS"
    finding = _finding(report, "data.metric.target_observation")
    assert finding.severity == "FAIL"
    assert "exactly one is required" in finding.message
    assert report.verdict == "BLOCK"


def test_unsupported_operator_blocks() -> None:
    report = _chart(
        "Conversion met target.",
        target_operator="above",
    ).audit()

    assert _finding(report, "contract.metric.target").severity == "FAIL"
    assert report.verdict == "BLOCK"


def test_negative_tolerance_blocks() -> None:
    report = _chart(
        "Conversion met target.",
        target_tolerance=-0.1,
    ).audit()

    assert _finding(report, "contract.metric.target").severity == "FAIL"


def test_first_party_spec_preserves_target_receipts_and_visible_rule() -> None:
    spec = _chart("Conversion met target.").to_vega_lite()

    assert spec["usermeta"]["target_contract"] == {
        "version": 1,
        "metric_field": "conversion_rate",
        "selector_field": "period",
        "selector_value": "after",
        "target_value": 0.8,
        "operator": "at_least",
        "tolerance": 0.0,
        "observed_value": 0.81,
        "target_gap": 0.010000000000000009,
        "target_met": True,
    }

    layers = spec.get("layer", [])
    assert any(
        isinstance(layer.get("mark"), dict)
        and layer["mark"].get("type") == "rule"
        and layer.get("encoding", {}).get("y", {}).get("datum") == 0.8
        for layer in layers
    )


def _external_spec() -> tuple[dict, pd.DataFrame]:
    frame = _frame()
    spec = {
        "title": "Observed conversion rate",
        "layer": [
            {
                "mark": {"type": "line", "point": True},
                "encoding": {
                    "x": {"field": "period", "type": "ordinal"},
                    "y": {"field": "conversion_rate", "type": "quantitative"},
                },
            },
            {
                "mark": {"type": "rule"},
                "encoding": {
                    "y": {"datum": 0.80},
                },
            },
        ],
        "usermeta": {
            "source": "synthetic.targets",
            "unit": "score",
            "target_contract": {
                "version": 1,
                "metric_field": "conversion_rate",
                "selector_field": "period",
                "selector_value": "after",
                "target_value": 0.80,
                "operator": "at_least",
                "tolerance": 0.0,
                "observed_value": 0.81,
                "target_gap": 0.010000000000000009,
                "target_met": True,
            },
        },
    }
    return spec, frame


def test_external_target_contract_passes() -> None:
    spec, frame = _external_spec()

    report = audit_spec(spec, data=frame, claim="Conversion met target.")

    assert _finding(report, "contract.metric.target").severity == "PASS"
    assert _finding(report, "data.metric.target_observation").severity == "PASS"
    assert _finding(report, "visual.metric.target").severity == "PASS"
    assert _finding(report, "claim.metric.target_semantics").severity == "PASS"
    assert report.verdict == "READY"


def test_external_missing_target_rule_blocks() -> None:
    spec, frame = _external_spec()
    spec["layer"] = [spec["layer"][0]]

    report = audit_spec(spec, data=frame, claim="Conversion met target.")

    assert _finding(report, "visual.metric.target").severity == "FAIL"
    assert report.verdict == "BLOCK"


def test_external_wrong_target_rule_blocks() -> None:
    spec, frame = _external_spec()
    spec["layer"][1]["encoding"]["y"]["datum"] = 0.90

    report = audit_spec(spec, data=frame, claim="Conversion met target.")

    assert _finding(report, "visual.metric.target").severity == "FAIL"


def test_external_stale_receipts_block() -> None:
    spec, frame = _external_spec()
    spec["usermeta"]["target_contract"]["observed_value"] = 0.79
    spec["usermeta"]["target_contract"]["target_met"] = False

    report = audit_spec(spec, data=frame, claim="Conversion met target.")

    assert _finding(report, "data.metric.target_observation").severity == "FAIL"
    assert report.verdict == "BLOCK"


def test_external_target_metric_must_be_visible_quantitative_field() -> None:
    spec, frame = _external_spec()
    spec["usermeta"]["target_contract"]["metric_field"] = "other"

    report = audit_spec(spec, data=frame, claim="Conversion met target.")

    assert _finding(report, "contract.metric.target").severity == "FAIL"


def test_external_target_contract_requires_reconstructable_evidence() -> None:
    spec, _ = _external_spec()

    report = audit_spec(spec, data=None, claim="Conversion met target.")

    assert _finding(report, "data.metric.target_observation").severity == "FAIL"


def test_closed_target_schema_blocks_extra_fields() -> None:
    spec, frame = _external_spec()
    spec["usermeta"]["target_contract"]["target_owner"] = "Finance"

    report = audit_spec(spec, data=frame, claim="Conversion met target.")

    assert _finding(report, "contract.metric.target").severity == "FAIL"


def test_mixed_met_and_missed_wording_blocks() -> None:
    report = _chart("Conversion met target but also missed the target.").audit()

    assert _finding(report, "claim.metric.target_semantics").severity == "FAIL"


def test_ordinary_claim_without_target_metadata_does_not_invent_target_semantics() -> None:
    chart = Chart.trend(
        data=_frame(),
        x="period",
        y="conversion_rate",
        claim="Conversion increased.",
        source="synthetic.targets",
        unit="rate",
        title="Observed conversion rate",
    )

    report = chart.audit()

    assert not any(
        f.rule_id.startswith("claim.metric.target") or f.rule_id == "contract.metric.target"
        for f in report.findings
    )
