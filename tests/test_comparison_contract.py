from __future__ import annotations

from copy import deepcopy

import pandas as pd
import pytest

from chart_contract import Chart, audit_spec


def _severity(report, rule_id: str) -> str:
    return next(f.severity for f in report.findings if f.rule_id == rule_id)


def _trend(
    values=(100.0, 120.0),
    *,
    claim="Revenue increased by 20%.",
    unit="dollars",
    value_representation=None,
    change_type="percent_change",
    declared_change=20.0,
) -> Chart:
    return Chart.trend(
        data=pd.DataFrame({"period": ["2025", "2026"], "metric": list(values)}),
        x="period",
        y="metric",
        claim=claim,
        source="synthetic.baseline",
        unit=unit,
        value_representation=value_representation,
        title="Observed comparison",
        baseline_field="period",
        baseline_value="2025",
        target_value="2026",
        change_type=change_type,
        declared_change=declared_change,
        window_kind="calendar",
        window_granularity="year",
        baseline_start="2025-01-01",
        baseline_end="2025-12-31",
        target_start="2026-01-01",
        target_end="2026-12-31",
        baseline_complete=True,
        target_complete=True,
    )


def test_percent_change_contract_recomputes_against_baseline() -> None:
    report = _trend().audit()

    assert _severity(report, "contract.comparison.baseline") == "PASS"
    assert _severity(report, "data.comparison.baseline") == "PASS"
    assert _severity(report, "contract.comparison.change") == "PASS"
    assert _severity(report, "claim.comparison.change_semantics") == "PASS"
    assert report.verdict == "READY"


def test_first_party_spec_stamps_observed_values_and_change_receipt() -> None:
    spec = _trend().to_vega_lite()

    assert spec["usermeta"]["comparison_contract"] == {
        "version": 1,
        "metric_field": "metric",
        "baseline_field": "period",
        "baseline_value": "2025",
        "target_value": "2026",
        "change_type": "percent_change",
        "declared_change": 20.0,
        "baseline_metric_value": 100.0,
        "target_metric_value": 120.0,
        "computed_change": 20.0,
    }


def test_wrong_declared_percent_change_blocks() -> None:
    report = _trend(declared_change=18.0, claim="Revenue increased.").audit()

    assert _severity(report, "contract.comparison.change") == "FAIL"
    assert report.verdict == "BLOCK"


def test_claim_percent_value_must_match_contract() -> None:
    report = _trend(claim="Revenue increased by 18%.").audit()

    assert _severity(report, "claim.comparison.change_semantics") == "FAIL"
    assert report.verdict == "BLOCK"


def test_claim_percent_cannot_masquerade_as_percentage_points() -> None:
    chart = _trend(
        values=(40.0, 60.0),
        claim="Conversion increased by 20%.",
        unit="percent",
        value_representation="percentage_points",
        change_type="percentage_points",
        declared_change=20.0,
    )
    chart.numerator = "converted_sessions"
    chart.denominator = "eligible_sessions"

    report = chart.audit()

    assert _severity(report, "contract.comparison.change") == "PASS"
    assert _severity(report, "claim.comparison.change_semantics") == "FAIL"
    assert report.verdict == "BLOCK"


def test_percentage_point_claim_and_arithmetic_pass() -> None:
    chart = _trend(
        values=(0.40, 0.45),
        claim="Conversion increased by 5 percentage points.",
        unit="percent",
        value_representation="fraction",
        change_type="percentage_points",
        declared_change=5.0,
    )
    chart.numerator = "converted_sessions"
    chart.denominator = "eligible_sessions"

    report = chart.audit()

    assert _severity(report, "contract.comparison.change") == "PASS"
    assert _severity(report, "claim.comparison.change_semantics") == "PASS"
    assert report.verdict == "READY"


def test_percentage_points_require_percent_source_semantics() -> None:
    report = _trend(
        values=(40.0, 45.0),
        claim="Metric increased.",
        unit="points",
        change_type="percentage_points",
        declared_change=5.0,
    ).audit()

    assert _severity(report, "data.comparison.baseline") == "FAIL"
    assert report.verdict == "BLOCK"


def test_ratio_change_and_claim_pass() -> None:
    report = _trend(
        values=(50.0, 100.0),
        claim="The target is 2x the baseline.",
        change_type="ratio",
        declared_change=2.0,
    ).audit()

    assert _severity(report, "contract.comparison.change") == "PASS"
    assert _severity(report, "claim.comparison.change_semantics") == "PASS"


def test_absolute_delta_passes_without_forcing_claim_nlp() -> None:
    report = _trend(
        values=(100.0, 125.0),
        claim="Revenue increased from baseline to target.",
        change_type="absolute",
        declared_change=25.0,
    ).audit()

    assert _severity(report, "contract.comparison.change") == "PASS"
    assert _severity(report, "claim.comparison.change_semantics") == "PASS"


def test_explicit_numeric_change_claim_without_contract_requires_review() -> None:
    chart = Chart.trend(
        data=pd.DataFrame({"period": ["2025", "2026"], "revenue": [100.0, 120.0]}),
        x="period",
        y="revenue",
        claim="Revenue increased by 20%.",
        source="synthetic.baseline",
        unit="dollars",
        title="Observed revenue comparison",
    )

    report = chart.audit()

    assert _severity(report, "contract.comparison.baseline") == "WARN"
    assert report.verdict == "REVIEW"


def test_baseline_selector_must_resolve_exactly_one_row() -> None:
    chart = Chart.compare(
        data=pd.DataFrame(
            {
                "period": ["2025", "2025", "2026"],
                "metric": [100.0, 101.0, 120.0],
            }
        ),
        x="period",
        y="metric",
        claim="Observed comparison.",
        source="synthetic.baseline",
        unit="dollars",
        title="Observed comparison",
        baseline_field="period",
        baseline_value="2025",
        target_value="2026",
        change_type="absolute",
        declared_change=20.0,
    )

    report = chart.audit()

    assert _severity(report, "data.comparison.baseline") == "FAIL"
    assert report.verdict == "BLOCK"


def test_baseline_field_must_be_visible_dimension() -> None:
    chart = Chart.trend(
        data=pd.DataFrame(
            {
                "period": ["2025", "2026"],
                "hidden_id": ["before", "after"],
                "metric": [100.0, 120.0],
            }
        ),
        x="period",
        y="metric",
        claim="Observed comparison.",
        source="synthetic.baseline",
        unit="dollars",
        title="Observed comparison",
        baseline_field="hidden_id",
        baseline_value="before",
        target_value="after",
        change_type="absolute",
        declared_change=20.0,
    )

    report = chart.audit()

    assert _severity(report, "contract.comparison.baseline") == "FAIL"


def test_zero_baseline_blocks_percent_change_and_ratio() -> None:
    percent_report = _trend(
        values=(0.0, 10.0),
        claim="Observed comparison.",
        change_type="percent_change",
        declared_change=100.0,
    ).audit()
    ratio_report = _trend(
        values=(0.0, 10.0),
        claim="Observed comparison.",
        change_type="ratio",
        declared_change=2.0,
    ).audit()

    assert _severity(percent_report, "data.comparison.baseline") == "FAIL"
    assert _severity(ratio_report, "data.comparison.baseline") == "FAIL"


def _spec() -> tuple[dict, pd.DataFrame]:
    frame = pd.DataFrame({"period": ["2025", "2026"], "revenue": [100.0, 120.0]})
    spec = {
        "mark": "line",
        "title": "Observed revenue comparison",
        "encoding": {
            "x": {"field": "period", "type": "ordinal"},
            "y": {"field": "revenue", "type": "quantitative"},
        },
        "usermeta": {
            "source": "synthetic.baseline",
            "unit": "dollars",
            "comparison_contract": {
                "version": 1,
                "metric_field": "revenue",
                "baseline_field": "period",
                "baseline_value": "2025",
                "target_value": "2026",
                "change_type": "percent_change",
                "declared_change": 20.0,
                "baseline_metric_value": 100.0,
                "target_metric_value": 120.0,
                "computed_change": 20.0,
            },
            "time_window_contract": {
                "version": 1,
                "window_kind": "calendar",
                "window_granularity": "year",
                "baseline_start": "2025-01-01",
                "baseline_end": "2025-12-31",
                "target_start": "2026-01-01",
                "target_end": "2026-12-31",
                "baseline_complete": True,
                "target_complete": True,
                "baseline_days": 365,
                "target_days": 365,
            },
        },
    }
    return spec, frame


def test_external_comparison_contract_passes() -> None:
    spec, frame = _spec()

    report = audit_spec(spec, data=frame, claim="Revenue increased by 20%.")

    assert _severity(report, "contract.comparison.baseline") == "PASS"
    assert _severity(report, "data.comparison.baseline") == "PASS"
    assert _severity(report, "contract.comparison.change") == "PASS"
    assert _severity(report, "claim.comparison.change_semantics") == "PASS"
    assert report.verdict == "READY"


def test_external_stale_computed_receipt_blocks() -> None:
    spec, frame = _spec()
    spec["usermeta"]["comparison_contract"]["computed_change"] = 18.0

    report = audit_spec(spec, data=frame, claim="Revenue increased by 20%.")

    assert _severity(report, "contract.comparison.change") == "FAIL"
    assert report.verdict == "BLOCK"


def test_external_percent_vs_percentage_point_claim_mismatch_blocks() -> None:
    frame = pd.DataFrame({"period": ["2025", "2026"], "conversion": [40.0, 60.0]})
    spec = {
        "mark": "line",
        "title": "Observed conversion comparison",
        "encoding": {
            "x": {"field": "period", "type": "ordinal"},
            "y": {"field": "conversion", "type": "quantitative"},
        },
        "usermeta": {
            "source": "synthetic.baseline",
            "unit": "percent",
            "value_representation": "percentage_points",
            "ratio_contract": {
                "version": 1,
                "metric_field": "conversion",
                "numerator": "converted_sessions",
                "denominator": "eligible_sessions",
                "cohort": None,
                "denominator_basis_field": None,
            },
            "comparison_contract": {
                "version": 1,
                "metric_field": "conversion",
                "baseline_field": "period",
                "baseline_value": "2025",
                "target_value": "2026",
                "change_type": "percentage_points",
                "declared_change": 20.0,
                "baseline_metric_value": 40.0,
                "target_metric_value": 60.0,
                "computed_change": 20.0,
            },
        },
    }

    report = audit_spec(spec, data=frame, claim="Conversion increased by 20%.")

    assert _severity(report, "contract.comparison.change") == "PASS"
    assert _severity(report, "claim.comparison.change_semantics") == "FAIL"
    assert report.verdict == "BLOCK"


def test_external_contract_requires_evidence() -> None:
    spec, _ = _spec()

    report = audit_spec(spec, data=None, claim="Revenue increased by 20%.")

    assert _severity(report, "data.comparison.baseline") == "FAIL"


def test_closed_comparison_schema_blocks_extra_fields() -> None:
    spec, frame = _spec()
    spec["usermeta"]["comparison_contract"]["round_digits"] = 1

    report = audit_spec(spec, data=frame, claim="Revenue increased by 20%.")

    assert _severity(report, "contract.comparison.baseline") == "FAIL"


def test_renderer_refuses_wrong_declared_change() -> None:
    with pytest.raises(ValueError):
        # Rendering computes the durable receipt from the final source evidence.
        _trend(declared_change=18.0).to_vega_lite()
