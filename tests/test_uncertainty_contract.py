from __future__ import annotations

from copy import deepcopy

import pandas as pd
import pytest

from chart_contract import Chart, audit_spec


def _finding(report, rule_id: str):
    return next(f for f in report.findings if f.rule_id == rule_id)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "period": ["before", "after"],
            "estimate": [10.0, 12.0],
            "lower": [8.0, 10.5],
            "upper": [12.0, 13.5],
        }
    )


def _chart(frame: pd.DataFrame, **overrides) -> Chart:
    kwargs = {
        "data": frame,
        "x": "period",
        "y": "estimate",
        "claim": "Observed estimates are shown with uncertainty intervals.",
        "source": "synthetic.uncertainty",
        "unit": "users",
        "title": "Observed estimates",
        "interval_lower_field": "lower",
        "interval_upper_field": "upper",
        "interval_kind": "confidence",
        "interval_level": 0.95,
        "interval_method": "wald",
    }
    kwargs.update(overrides)
    return Chart.trend(**kwargs)


def test_valid_uncertainty_contract_passes() -> None:
    report = _chart(_frame()).audit()

    assert _finding(report, "contract.uncertainty.interval").severity == "PASS"
    assert _finding(report, "data.uncertainty.bounds").severity == "PASS"
    assert report.verdict == "READY"


def test_first_party_spec_preserves_contract_and_visible_interval_rule() -> None:
    frame = _frame()
    spec = _chart(frame).to_vega_lite()

    assert spec["usermeta"]["uncertainty_contract"] == {
        "version": 1,
        "estimate_field": "estimate",
        "lower_field": "lower",
        "upper_field": "upper",
        "interval_kind": "confidence",
        "interval_level": 0.95,
        "interval_method": "wald",
    }

    report = audit_spec(
        spec,
        data=frame,
        claim="Observed estimates are shown with uncertainty intervals.",
    )
    assert _finding(report, "visual.uncertainty.interval").severity == "PASS"
    assert report.verdict == "READY"


def test_invalid_bound_order_blocks_and_refuses_render() -> None:
    frame = _frame()
    frame.loc[1, "lower"] = 12.5
    chart = _chart(frame)

    report = chart.audit()

    finding = _finding(report, "data.uncertainty.bounds")
    assert finding.severity == "FAIL"
    assert "lower <= estimate <= upper" in finding.message
    assert report.verdict == "BLOCK"

    with pytest.raises(ValueError, match="lower <= estimate <= upper"):
        chart.to_vega_lite()


@pytest.mark.parametrize(
    "column",
    ["estimate", "lower", "upper"],
)
def test_missing_interval_values_block(column: str) -> None:
    frame = _frame()
    frame.loc[0, column] = None

    report = _chart(frame).audit()

    assert _finding(report, "data.uncertainty.bounds").severity == "FAIL"
    assert report.verdict == "BLOCK"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"interval_lower_field": None}, "lower_field"),
        ({"interval_upper_field": None}, "upper_field"),
        ({"interval_kind": "standard_error"}, "interval_kind"),
        ({"interval_level": 0.0}, "interval_level"),
        ({"interval_level": 1.0}, "interval_level"),
        ({"interval_method": ""}, "interval_method"),
        ({"interval_lower_field": "estimate"}, "must be distinct"),
    ],
)
def test_partial_or_malformed_contract_blocks(overrides, message) -> None:
    report = _chart(_frame(), **overrides).audit()

    finding = _finding(report, "contract.uncertainty.interval")
    assert finding.severity == "FAIL"
    assert message in finding.message
    assert report.verdict == "BLOCK"


def test_explicit_interval_claim_without_contract_requires_review() -> None:
    chart = Chart.trend(
        data=_frame(),
        x="period",
        y="estimate",
        claim="The estimates are shown with a 95% confidence interval.",
        source="synthetic.uncertainty",
        unit="users",
        title="Observed estimates",
    )

    report = chart.audit()

    finding = _finding(report, "claim.uncertainty.semantics")
    assert finding.severity == "WARN"
    assert not any(
        f.rule_id == "contract.comparison.baseline" for f in report.findings
    )
    assert report.verdict == "REVIEW"


def test_explicit_interval_claim_matches_contract() -> None:
    report = _chart(
        _frame(),
        claim="The estimates are shown with a 95% confidence interval.",
    ).audit()

    assert _finding(report, "claim.uncertainty.semantics").severity == "PASS"
    assert report.verdict == "READY"


def test_explicit_interval_claim_kind_mismatch_blocks() -> None:
    report = _chart(
        _frame(),
        claim="The estimates are shown with a 95% credible interval.",
    ).audit()

    finding = _finding(report, "claim.uncertainty.semantics")
    assert finding.severity == "FAIL"
    assert "credible" in finding.message
    assert "confidence" in finding.message
    assert report.verdict == "BLOCK"


def test_explicit_interval_claim_level_mismatch_blocks() -> None:
    report = _chart(
        _frame(),
        claim="The estimates are shown with a 90% confidence interval.",
    ).audit()

    finding = _finding(report, "claim.uncertainty.semantics")
    assert finding.severity == "FAIL"
    assert "0.900" in finding.message
    assert "0.950" in finding.message
    assert report.verdict == "BLOCK"


def _external_spec() -> tuple[dict, pd.DataFrame]:
    frame = _frame()
    spec = {
        "title": "Observed estimates",
        "layer": [
            {
                "mark": "line",
                "encoding": {
                    "x": {"field": "period", "type": "ordinal"},
                    "y": {"field": "estimate", "type": "quantitative"},
                },
            },
            {
                "mark": "rule",
                "encoding": {
                    "x": {"field": "period", "type": "ordinal"},
                    "y": {"field": "lower", "type": "quantitative"},
                    "y2": {"field": "upper"},
                },
            },
        ],
        "usermeta": {
            "source": "synthetic.uncertainty",
            "unit": "users",
            "uncertainty_contract": {
                "version": 1,
                "estimate_field": "estimate",
                "lower_field": "lower",
                "upper_field": "upper",
                "interval_kind": "confidence",
                "interval_level": 0.95,
                "interval_method": "wald",
            },
        },
    }
    return spec, frame


def test_external_interval_contract_passes() -> None:
    spec, frame = _external_spec()

    report = audit_spec(
        spec,
        data=frame,
        claim="Observed estimates are shown with uncertainty intervals.",
    )

    assert _finding(report, "contract.uncertainty.interval").severity == "PASS"
    assert _finding(report, "data.uncertainty.bounds").severity == "PASS"
    assert _finding(report, "visual.uncertainty.interval").severity == "PASS"
    assert report.verdict == "READY"


def test_external_interval_metadata_without_visible_bounds_blocks() -> None:
    spec, frame = _external_spec()
    spec["layer"] = spec["layer"][:1]

    report = audit_spec(
        spec,
        data=frame,
        claim="Observed estimates are shown with uncertainty intervals.",
    )

    assert _finding(report, "visual.uncertainty.interval").severity == "FAIL"
    assert report.verdict == "BLOCK"


def test_external_tampered_estimate_binding_blocks() -> None:
    spec, frame = _external_spec()
    spec["usermeta"]["uncertainty_contract"]["estimate_field"] = "estimate_old"
    frame["estimate_old"] = frame["estimate"]

    report = audit_spec(
        spec,
        data=frame,
        claim="Observed estimates are shown with uncertainty intervals.",
    )

    assert _finding(report, "visual.uncertainty.interval").severity == "FAIL"
    assert report.verdict == "BLOCK"


def test_external_tampered_interval_binding_blocks() -> None:
    spec, frame = _external_spec()
    spec["layer"][1]["encoding"]["y"]["field"] = "estimate"

    report = audit_spec(
        spec,
        data=frame,
        claim="Observed estimates are shown with uncertainty intervals.",
    )

    assert _finding(report, "visual.uncertainty.interval").severity == "FAIL"


def test_external_interval_contract_requires_reconstructable_evidence() -> None:
    spec, _ = _external_spec()

    report = audit_spec(
        spec,
        data=None,
        claim="Observed estimates are shown with uncertainty intervals.",
    )

    assert _finding(report, "data.uncertainty.bounds").severity == "FAIL"
    assert report.verdict == "BLOCK"


def test_closed_uncertainty_schema_blocks_extra_fields() -> None:
    spec, frame = _external_spec()
    spec["usermeta"]["uncertainty_contract"]["standard_error_field"] = "se"

    report = audit_spec(
        spec,
        data=frame,
        claim="Observed estimates are shown with uncertainty intervals.",
    )

    assert _finding(report, "contract.uncertainty.interval").severity == "FAIL"


def test_compare_renders_grouped_interval_rules() -> None:
    frame = pd.DataFrame(
        {
            "segment": ["A", "A", "B", "B"],
            "group": ["control", "test", "control", "test"],
            "estimate": [10.0, 11.0, 12.0, 13.0],
            "lower": [9.0, 10.0, 11.0, 12.0],
            "upper": [11.0, 12.0, 13.0, 14.0],
        }
    )
    chart = Chart.compare(
        data=frame,
        x="segment",
        y="estimate",
        group="group",
        claim="Observed estimates are shown by segment and group.",
        source="synthetic.uncertainty",
        unit="users",
        title="Grouped estimates",
        interval_lower_field="lower",
        interval_upper_field="upper",
        interval_kind="bootstrap",
        interval_level=0.9,
        interval_method="percentile bootstrap",
    )

    spec = chart.to_vega_lite()
    report = audit_spec(spec, data=frame, claim=chart.claim)

    assert _finding(report, "visual.uncertainty.interval").severity == "PASS"
    assert report.verdict == "READY"
