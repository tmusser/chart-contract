from __future__ import annotations

import copy

import pandas as pd
import pytest

from chart_contract import Chart, audit_spec


def _finding(report, rule_id: str):
    return next(item for item in report.findings if item.rule_id == rule_id)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "period": ["Jan", "Feb", "Mar"],
            "conversion_rate": [0.2, 0.3, 0.4],
            "conversions": [20, 30, 40],
            "sessions": [100, 100, 100],
        }
    )


def _chart(data=None, *, intent="trend", **overrides) -> Chart:
    args = {
        "data": _frame() if data is None else data,
        "x": "period",
        "y": "conversion_rate",
        "claim": "Observed monthly conversion rates are shown.",
        "source": "synthetic.ratios",
        "unit": "conversion rate",
        "title": "Monthly conversion rate",
        "numerator": "converted_sessions",
        "denominator": "eligible_sessions",
        "numerator_value_field": "conversions",
        "denominator_value_field": "sessions",
    }
    args.update(overrides)
    return getattr(Chart, intent)(**args)


@pytest.mark.parametrize("intent", ["trend", "rank", "compare"])
def test_v2_numeric_ratio_ready_for_all_three_intents(intent: str) -> None:
    chart = _chart(intent=intent)
    report = chart.audit()
    assert _finding(report, "contract.ratio.denominator").severity == "PASS"
    assert _finding(report, "data.ratio.arithmetic").severity == "PASS"
    assert report.verdict == "READY"
    contract = chart.to_vega_lite()["usermeta"]["ratio_contract"]
    assert contract == {
        "version": 2,
        "metric_field": "conversion_rate",
        "numerator": "converted_sessions",
        "denominator": "eligible_sessions",
        "cohort": None,
        "denominator_basis_field": None,
        "numerator_value_field": "conversions",
        "denominator_value_field": "sessions",
        "ratio_multiplier": 1.0,
        "ratio_tolerance": 1e-9,
    }


def test_wrong_reported_rate_blocks_and_refuses_first_party_render() -> None:
    frame = _frame()
    frame.loc[1, "conversion_rate"] = 0.4
    chart = _chart(frame)
    report = chart.audit()
    assert _finding(report, "contract.ratio.denominator").severity == "PASS"
    bad = _finding(report, "data.ratio.arithmetic")
    assert bad.severity == "FAIL"
    assert "row 2" in bad.message and "computed 0.3" in bad.message
    assert report.verdict == "BLOCK"
    with pytest.raises(ValueError, match="Ratio arithmetic mismatch"):
        chart.to_vega_lite()


@pytest.mark.parametrize(
    ("field", "value", "fragment"),
    [
        ("sessions", 0, "zero or negative"),
        ("sessions", -1, "zero or negative"),
        ("sessions", None, "non-finite or non-numeric"),
        ("sessions", float("inf"), "non-finite or non-numeric"),
        ("conversions", "bad", "non-finite or non-numeric"),
        ("conversions", True, "non-finite or non-numeric"),
        ("conversion_rate", float("nan"), "non-finite or non-numeric"),
    ],
)
def test_bad_row_level_arithmetic_evidence_blocks(field, value, fragment) -> None:
    frame = _frame()
    frame[field] = frame[field].astype(object)
    frame.at[1, field] = value
    report = _chart(frame).audit()
    finding = _finding(report, "data.ratio.arithmetic")
    assert finding.severity == "FAIL"
    assert fragment in finding.message


def test_missing_evidence_field_blocks() -> None:
    report = _chart(_frame().drop(columns=["sessions"])).audit()
    assert "missing" in _finding(report, "data.ratio.arithmetic").message
    assert report.verdict == "BLOCK"


def test_percentage_point_scaling_and_absolute_tolerance() -> None:
    frame = _frame()
    frame["conversion_rate"] = [20.0, 30.0, 40.0005]
    chart = _chart(
        frame, unit="percent", value_representation="percentage_points",
        ratio_multiplier=100, ratio_tolerance=0.001,
    )
    assert _finding(chart.audit(), "data.ratio.arithmetic").severity == "PASS"
    assert chart.to_vega_lite()["usermeta"]["ratio_contract"]["ratio_multiplier"] == 100.0


def test_out_of_tolerance_blocks() -> None:
    frame = _frame()
    frame.at[2, "conversion_rate"] = 0.4001
    report = _chart(frame, ratio_tolerance=0.00001).audit()
    assert _finding(report, "data.ratio.arithmetic").severity == "FAIL"


def test_zero_numerator_with_positive_denominator_valid() -> None:
    frame = _frame()
    frame.at[0, "conversions"] = 0
    frame.at[0, "conversion_rate"] = 0.0
    assert _finding(_chart(frame).audit(), "data.ratio.arithmetic").severity == "PASS"


def test_v1_remains_metadata_only() -> None:
    chart = _chart(numerator_value_field=None, denominator_value_field=None)
    report = chart.audit()
    assert report.verdict == "READY"
    assert all(f.rule_id != "data.ratio.arithmetic" for f in report.findings)
    assert chart.to_vega_lite()["usermeta"]["ratio_contract"]["version"] == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"denominator_value_field": None},
        {"ratio_multiplier": 0},
        {"ratio_multiplier": -1},
        {"ratio_multiplier": True},
        {"ratio_multiplier": float("inf")},
        {"ratio_tolerance": -1},
        {"ratio_tolerance": True},
        {"ratio_tolerance": float("nan")},
        {"numerator_value_field": "sessions"},
        {"numerator_value_field": "conversion_rate"},
    ],
)
def test_partial_or_invalid_v2_contract_blocks(overrides) -> None:
    report = _chart(**overrides).audit()
    assert _finding(report, "contract.ratio.denominator").severity == "FAIL"
    assert report.verdict == "BLOCK"


def test_external_spec_valid_evidence_and_tampering() -> None:
    chart = _chart()
    spec = chart.to_vega_lite()
    clean = audit_spec(spec=spec, data=_frame(), claim=chart.claim)
    assert _finding(clean, "data.ratio.arithmetic").severity == "PASS"

    bad = _frame()
    bad.at[1, "conversion_rate"] = 0.4
    report = audit_spec(spec=spec, data=bad, claim=chart.claim)
    assert _finding(report, "data.ratio.arithmetic").severity == "FAIL"
    assert report.verdict == "BLOCK"


def test_external_spec_without_reconstructable_evidence_blocks() -> None:
    chart = _chart()
    spec = chart.to_vega_lite()
    spec.pop("data", None)
    spec.pop("datasets", None)
    report = audit_spec(spec=spec, data=None, claim=chart.claim)
    assert _finding(report, "data.ratio.arithmetic").severity == "FAIL"


def test_external_closed_v2_schema_blocks_unknown_field() -> None:
    chart = _chart()
    spec = copy.deepcopy(chart.to_vega_lite())
    spec["usermeta"]["ratio_contract"]["invented_receipt"] = 3
    report = audit_spec(spec=spec, data=_frame(), claim=chart.claim)
    assert _finding(report, "contract.ratio.denominator").severity == "FAIL"


def test_empty_evidence_fails_arithmetic() -> None:
    report = _chart(_frame().iloc[:0]).audit()
    assert _finding(report, "data.ratio.arithmetic").severity == "FAIL"
