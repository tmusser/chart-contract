from __future__ import annotations

from copy import deepcopy

import pandas as pd
import pytest

from chart_contract import Chart, audit_spec


def _finding(report, rule_id: str):
    return next(f for f in report.findings if f.rule_id == rule_id)


def _rank_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "region": ["East", "West", "Central"],
            "revenue": [40.0, 35.0, 25.0],
        }
    )


def _rank_chart(frame: pd.DataFrame, **overrides) -> Chart:
    kwargs = {
        "data": frame,
        "x": "region",
        "y": "revenue",
        "claim": "Regional revenue components are shown.",
        "source": "synthetic.regional_revenue",
        "unit": "USD millions",
        "title": "Regional revenue",
        "control_total": 100.0,
        "control_total_source": "finance.company_total",
        "reconciliation_tolerance": 0.0,
    }
    kwargs.update(overrides)
    return Chart.rank(**kwargs)


def test_exact_control_total_reconciliation_passes() -> None:
    report = _rank_chart(_rank_frame()).audit()

    assert _finding(report, "contract.reconciliation.control_total").severity == "PASS"
    assert _finding(report, "data.reconciliation.components").severity == "PASS"
    assert _finding(report, "data.reconciliation.total").severity == "PASS"
    assert report.verdict == "READY"


def test_first_party_spec_preserves_reconciliation_receipts() -> None:
    spec = _rank_chart(_rank_frame()).to_vega_lite()

    assert spec["usermeta"]["reconciliation_contract"] == {
        "version": 1,
        "component_field": "region",
        "metric_field": "revenue",
        "reconciliation": "sum",
        "control_total": 100.0,
        "control_total_source": "finance.company_total",
        "tolerance": 0.0,
        "component_count": 3,
        "component_total": 100.0,
        "residual": 0.0,
        "represented_share": 1.0,
    }


def test_missing_component_mass_blocks_and_renderer_refuses() -> None:
    chart = _rank_chart(_rank_frame(), control_total=118.0)

    report = chart.audit()

    finding = _finding(report, "data.reconciliation.total")
    assert finding.severity == "FAIL"
    assert "84.7% represented" in finding.message
    assert "residual=18" in finding.message
    assert report.verdict == "BLOCK"
    with pytest.raises(ValueError, match="does not reconcile"):
        chart.to_vega_lite()


def test_declared_tolerance_can_absorb_small_rounding_residual() -> None:
    chart = _rank_chart(
        _rank_frame(),
        control_total=100.01,
        reconciliation_tolerance=0.02,
    )

    report = chart.audit()

    assert _finding(report, "data.reconciliation.total").severity == "PASS"
    assert report.verdict == "READY"


def test_duplicate_component_labels_block() -> None:
    frame = pd.DataFrame(
        {"region": ["East", "East"], "revenue": [40.0, 60.0]}
    )

    report = _rank_chart(frame).audit()

    finding = _finding(report, "data.reconciliation.components")
    assert finding.severity == "FAIL"
    assert "duplicate component labels" in finding.message
    assert report.verdict == "BLOCK"


@pytest.mark.parametrize(
    "values",
    [
        [40.0, None, 60.0],
        [40.0, float("inf"), 60.0],
        [40.0, "oops", 60.0],
        [40.0, True, 60.0],
    ],
)
def test_invalid_component_values_block(values) -> None:
    frame = pd.DataFrame(
        {"region": ["East", "West", "Central"], "revenue": values}
    )

    report = _rank_chart(frame).audit()

    assert _finding(report, "data.reconciliation.components").severity == "FAIL"
    assert report.verdict == "BLOCK"


def test_ratio_like_metrics_cannot_use_sum_reconciliation() -> None:
    frame = pd.DataFrame(
        {"segment": ["A", "B"], "conversion_rate": [0.2, 0.3]}
    )
    chart = Chart.rank(
        data=frame,
        x="segment",
        y="conversion_rate",
        claim="Observed conversion rates are shown.",
        source="synthetic.rates",
        unit="conversion rate",
        control_total=0.5,
    )

    report = chart.audit()

    finding = _finding(report, "contract.reconciliation.control_total")
    assert finding.severity == "FAIL"
    assert "percent/rate/ratio" in finding.message
    assert report.verdict == "BLOCK"


def test_compare_reconciliation_requires_one_row_per_component() -> None:
    frame = pd.DataFrame(
        {
            "region": ["East", "East", "West", "West"],
            "channel": ["web", "store", "web", "store"],
            "revenue": [20.0, 20.0, 30.0, 30.0],
        }
    )
    chart = Chart.compare(
        data=frame,
        x="region",
        y="revenue",
        group="channel",
        claim="Regional revenue is shown by channel.",
        source="synthetic.regional_channel",
        unit="USD millions",
        control_total=100.0,
    )

    report = chart.audit()

    assert _finding(report, "data.reconciliation.components").severity == "FAIL"
    assert report.verdict == "BLOCK"


def _external_spec() -> tuple[dict, pd.DataFrame]:
    frame = _rank_frame()
    spec = {
        "mark": "bar",
        "title": "Regional revenue",
        "encoding": {
            "x": {"field": "region", "type": "nominal"},
            "y": {"field": "revenue", "type": "quantitative"},
        },
        "usermeta": {
            "source": "synthetic.regional_revenue",
            "unit": "USD millions",
            "reconciliation_contract": {
                "version": 1,
                "component_field": "region",
                "metric_field": "revenue",
                "reconciliation": "sum",
                "control_total": 100.0,
                "control_total_source": "finance.company_total",
                "tolerance": 0.0,
                "component_count": 3,
                "component_total": 100.0,
                "residual": 0.0,
                "represented_share": 1.0,
            },
        },
    }
    return spec, frame


def test_external_reconciliation_contract_passes() -> None:
    spec, frame = _external_spec()

    report = audit_spec(
        spec,
        data=frame,
        claim="Regional revenue components are shown.",
    )

    assert _finding(report, "contract.reconciliation.control_total").severity == "PASS"
    assert _finding(report, "data.reconciliation.components").severity == "PASS"
    assert _finding(report, "data.reconciliation.total").severity == "PASS"
    assert report.verdict == "READY"


def test_external_missing_mass_is_explicit_failure_not_schema_failure() -> None:
    spec, frame = _external_spec()
    spec["usermeta"]["reconciliation_contract"].update(
        {
            "control_total": 118.0,
            "component_total": 100.0,
            "residual": 18.0,
            "represented_share": 100.0 / 118.0,
        }
    )

    report = audit_spec(
        spec,
        data=frame,
        claim="Regional revenue components are shown.",
    )

    assert _finding(report, "contract.reconciliation.control_total").severity == "PASS"
    finding = _finding(report, "data.reconciliation.total")
    assert finding.severity == "FAIL"
    assert "84.7% represented" in finding.message
    assert report.verdict == "BLOCK"


def test_external_stale_receipts_block() -> None:
    spec, frame = _external_spec()
    spec["usermeta"]["reconciliation_contract"]["component_total"] = 99.0
    spec["usermeta"]["reconciliation_contract"]["residual"] = 1.0

    report = audit_spec(
        spec,
        data=frame,
        claim="Regional revenue components are shown.",
    )

    finding = _finding(report, "data.reconciliation.total")
    assert finding.severity == "FAIL"
    assert "receipts do not match" in finding.message


def test_external_contract_requires_visible_component_and_metric_binding() -> None:
    spec, frame = _external_spec()
    bad = deepcopy(spec)
    bad["usermeta"]["reconciliation_contract"]["component_field"] = "division"

    report = audit_spec(
        bad,
        data=frame,
        claim="Regional revenue components are shown.",
    )

    assert _finding(report, "contract.reconciliation.control_total").severity == "FAIL"


def test_external_reconciliation_requires_reconstructable_evidence() -> None:
    spec, _ = _external_spec()

    report = audit_spec(
        spec,
        data=None,
        claim="Regional revenue components are shown.",
    )

    assert _finding(report, "data.reconciliation.components").severity == "FAIL"
    assert report.verdict == "BLOCK"


def test_closed_reconciliation_schema_blocks_extra_fields() -> None:
    spec, frame = _external_spec()
    spec["usermeta"]["reconciliation_contract"]["unknown_bucket"] = 0.0

    report = audit_spec(
        spec,
        data=frame,
        claim="Regional revenue components are shown.",
    )

    assert _finding(report, "contract.reconciliation.control_total").severity == "FAIL"


def test_absent_reconciliation_contract_does_not_invent_control_total() -> None:
    spec, frame = _external_spec()
    del spec["usermeta"]["reconciliation_contract"]

    report = audit_spec(
        spec,
        data=frame,
        claim="Regional revenue components are shown.",
    )

    assert not any(
        f.rule_id.startswith("contract.reconciliation")
        or f.rule_id.startswith("data.reconciliation")
        for f in report.findings
    )
