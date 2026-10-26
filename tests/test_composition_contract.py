from __future__ import annotations

from copy import deepcopy

import pandas as pd
import pytest

from chart_contract import Chart, audit_spec


def _finding(report, rule):
    return next(x for x in report.findings if x.rule_id == rule)


def _frame():
    return pd.DataFrame({
        "period": ["before", "before", "after", "after"],
        "cohort": ["high", "low", "high", "low"],
        "conversion_rate": [0.8, 0.2, 0.9, 0.3],
        "conversions": [80, 2, 9, 30],
        "sessions": [100, 10, 10, 100],
    })


def _chart(data=None, **overrides):
    kwargs = dict(
        data=_frame() if data is None else data,
        x="period",
        group="cohort",
        y="conversion_rate",
        claim="Observed subgroup conversion rates changed.",
        source="synthetic.funnel",
        unit="conversion rate",
        title="Conversion by cohort",
        numerator="conversions",
        denominator="sessions",
        numerator_value_field="conversions",
        denominator_value_field="sessions",
        composition_baseline_value="before",
        composition_target_value="after",
    )
    kwargs.update(overrides)
    return Chart.compare(**kwargs)


def test_true_simpson_reversal_is_warn_not_fail_and_receipts_reconstruct():
    chart = _chart()
    report = chart.audit()
    assert _finding(report, "contract.composition.declared").severity == "PASS"
    assert _finding(report, "data.composition.evidence").severity == "PASS"
    assert _finding(report, "data.composition.reversal").severity == "WARN"
    assert report.verdict == "REVIEW"
    saved = chart.to_vega_lite()["usermeta"]["composition_contract"]
    assert saved["group_count"] == 2
    assert saved["baseline_numerator"] == 82
    assert saved["baseline_denominator"] == 110
    assert saved["target_numerator"] == 39
    assert saved["target_denominator"] == 110
    assert saved["baseline_overall"] == pytest.approx(82 / 110)
    assert saved["target_overall"] == pytest.approx(39 / 110)
    assert saved["subgroup_direction"] == "up"
    assert saved["aggregate_direction"] == "down"
    assert saved["reversal"] is True


def test_first_party_and_external_spec_have_same_paradox_findings():
    chart = _chart()
    spec = chart.to_vega_lite()
    report = audit_spec(spec=spec, data=_frame(), claim=chart.claim)
    assert _finding(report, "contract.composition.declared").severity == "PASS"
    assert _finding(report, "data.composition.evidence").severity == "PASS"
    assert _finding(report, "data.composition.reversal").severity == "WARN"


def test_no_reversal_when_weights_stay_constant():
    frame = _frame()
    frame.loc[2, ["conversions", "sessions"]] = [90, 100]
    frame.loc[3, ["conversions", "sessions"]] = [3, 10]
    frame.loc[2, "conversion_rate"] = 0.9
    frame.loc[3, "conversion_rate"] = 0.3
    report = _chart(frame).audit()
    assert _finding(report, "data.composition.evidence").severity == "PASS"
    assert _finding(report, "data.composition.reversal").severity == "PASS"


def test_mixed_subgroup_directions_do_not_trigger_paradox():
    frame = _frame()
    frame.loc[3, "conversions"] = 10
    frame.loc[3, "conversion_rate"] = 0.1
    report = _chart(frame).audit()
    assert _finding(report, "data.composition.reversal").severity == "PASS"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda df: df.drop(index=[3]), "identical, complete subgroup sets"),
        (lambda df: pd.concat([df, df.iloc[[0]]], ignore_index=True), "duplicate period/subgroup key"),
        (lambda df: df.assign(cohort=["high", "low", "high", None]), "invalid subgroup"),
        (lambda df: df.assign(period=["before", "before", "after", "third"]), "undeclared period"),
        (lambda df: df.assign(sessions=[100, 10, 0, 100]), "zero or negative denominator"),
        (lambda df: df.assign(conversions=[80, 2, 11, 30]), "numerator exceeds denominator"),
        (lambda df: df.assign(conversions=[80, 2, -1, 30]), "at least 0"),
        (lambda df: df.assign(conversion_rate=[0.8, 0.2, 0.8, 0.3]), "inconsistent displayed rate"),
        (lambda df: df.drop(columns=["conversions"]), "missing field"),
        (lambda df: df.iloc[0:0], "cannot be empty"),
    ],
)
def test_invalid_evidence_blocks_and_renderer_refuses(mutation, message):
    frame = mutation(_frame())
    chart = _chart(frame)
    report = chart.audit()
    assert _finding(report, "data.composition.evidence").severity == "FAIL"
    assert message in _finding(report, "data.composition.evidence").message
    assert report.verdict == "BLOCK"
    with pytest.raises(ValueError):
        chart.to_vega_lite()


@pytest.mark.parametrize("value", [None, "", " ", False, "new"])
def test_malformed_composition_baseline_blocks(value):
    chart = _chart(composition_baseline_value=value)
    if value is None:
        # Declaring only the target opts in, which is not a complete contract.
        pass
    report = chart.audit()
    assert _finding(report, "contract.composition.declared").severity == "FAIL"


def test_unrelated_legacy_compare_does_not_gain_composition_rules():
    chart = _chart(composition_baseline_value=None, composition_target_value=None)
    report = chart.audit()
    assert not any(x.rule_id.startswith(("contract.composition", "data.composition")) for x in report.findings)
    assert "composition_contract" not in chart.to_vega_lite()["usermeta"]


def test_duplicate_subgroup_labels_across_periods_are_expected():
    chart = _chart()
    # A matched cohort necessarily recurs once per period, not once total.
    assert len(chart.data) == 4
    assert _finding(chart.audit(), "data.composition.evidence").severity == "PASS"


def test_stale_receipts_block_external_spec():
    chart = _chart()
    spec = deepcopy(chart.to_vega_lite())
    spec["usermeta"]["composition_contract"]["target_overall"] = 0.99
    report = audit_spec(spec=spec, data=_frame(), claim=chart.claim)
    assert _finding(report, "data.composition.evidence").severity == "FAIL"


def test_extra_contract_field_blocks():
    chart = _chart()
    spec = deepcopy(chart.to_vega_lite())
    spec["usermeta"]["composition_contract"]["extra"] = "not supported"
    report = audit_spec(spec=spec, data=_frame(), claim=chart.claim)
    assert _finding(report, "contract.composition.declared").severity == "FAIL"


def test_external_spec_requires_reconstructable_data():
    chart = _chart()
    spec = deepcopy(chart.to_vega_lite())
    spec.pop("data", None)
    spec.pop("datasets", None)
    report = audit_spec(spec=spec, data=None, claim=chart.claim)
    assert _finding(report, "data.composition.evidence").severity == "FAIL"


def test_external_spec_requires_visible_group_binding():
    chart = _chart()
    spec = deepcopy(chart.to_vega_lite())
    # Remove subgroup encodings only; preserve source and claim.
    spec["encoding"].pop("color", None)
    spec["encoding"].pop("xOffset", None)
    report = audit_spec(spec=spec, data=_frame(), claim=chart.claim)
    assert _finding(report, "contract.composition.declared").severity == "FAIL"


def test_composition_requires_at_least_two_groups():
    frame = _frame()
    frame = frame.loc[frame["cohort"] == "high"].reset_index(drop=True)
    chart = _chart(frame)
    assert _finding(chart.audit(), "data.composition.evidence").severity == "FAIL"


def test_noninteger_group_count_receipt_blocks():
    chart = _chart()
    spec = deepcopy(chart.to_vega_lite())
    spec["usermeta"]["composition_contract"]["group_count"] = True
    report = audit_spec(spec=spec, data=_frame(), claim=chart.claim)
    assert _finding(report, "contract.composition.declared").severity == "FAIL"


def test_reversal_receipt_cannot_be_silently_flipped():
    chart = _chart()
    spec = deepcopy(chart.to_vega_lite())
    spec["usermeta"]["composition_contract"]["reversal"] = False
    report = audit_spec(spec=spec, data=_frame(), claim=chart.claim)
    assert _finding(report, "data.composition.evidence").severity == "FAIL"
