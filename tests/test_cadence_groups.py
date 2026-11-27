"""Opt-in grouped trend cadence: missing subgroup-week evidence."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from chart_contract import Chart, audit_spec
from chart_contract.cadence_groups import (
    build_group_cadence_receipt,
    parse_group_cadence_contract,
)
from chart_contract.cli import main

TRAPS = Path(__file__).resolve().parents[1] / "examples" / "traps"
RULE = "data.trend.cadence.groups"


def _frame():
    return pd.DataFrame({
        "week": [
            "2026-10-05", "2026-10-05",
            "2026-10-12", "2026-10-12",
            "2026-10-19",
        ],
        "channel": ["Paid", "Organic", "Paid", "Organic", "Paid"],
        "sales": [100, 50, 110, 55, 120],
    })


def _chart(data=None, **kwargs):
    config = dict(
        data=_frame() if data is None else data,
        x="week", y="sales", group="channel",
        claim="Reported weekly systems across Paid and Organic.",
        source="synthetic.group_sales", title="Weekly sales by channel", unit="systems",
        cadence_frequency="weekly", cadence_require_complete=False,
        cadence_expected_groups=["Paid", "Organic"],
    )
    config.update(kwargs)
    return Chart.trend(**config)


def _finding(report, rule=RULE):
    return next(item for item in report.findings if item.rule_id == rule)


def test_organic_missing_week_warns_while_global_calendar_complete():
    chart = _chart()
    report = chart.audit()
    assert _finding(report).severity == "WARN"
    assert "Organic @ 2026-10-19" in _finding(report).message
    assert _finding(report, "contract.trend.cadence_groups").severity == "PASS"
    assert _finding(report, "data.trend.cadence_groups_evidence").severity == "PASS"
    assert not any(item.rule_id == "data.trend.cadence" for item in report.findings)
    receipt = chart.to_vega_lite()["usermeta"]["group_cadence_contract"]
    assert receipt["start_date"] == "2026-10-05"
    assert receipt["end_date"] == "2026-10-19"
    assert receipt["expected_period_count"] == 3
    assert receipt["expected_cell_count"] == 6
    assert receipt["observed_count"] == 5
    assert receipt["missing_count"] == 1
    assert receipt["missing_preview"] == [{"date": "2026-10-19", "group": "Organic"}]
    spec = chart.to_vega_lite()
    assert spec["encoding"]["color"]["field"] == "channel"
    assert "cadence_contract" not in spec["usermeta"]
    assert _finding(audit_spec(spec, data=chart.data)).severity == "WARN"


def test_complete_required_blocks_render_and_chart_audit():
    chart = _chart(cadence_require_complete=True)
    assert _finding(chart.audit()).severity == "FAIL"
    assert chart.audit().verdict == "BLOCK"
    with pytest.raises(ValueError, match="missing subgroup cadence"):
        chart.to_vega_lite()


def test_complete_group_grid_passes_and_spec_roundtrip():
    complete = pd.concat([
        _frame(),
        pd.DataFrame({"week": ["2026-10-19"], "channel": ["Organic"], "sales": [60]}),
    ], ignore_index=True)
    chart = _chart(complete, cadence_require_complete=True)
    assert _finding(chart.audit()).severity == "PASS"
    spec = chart.to_vega_lite()
    assert "cadence_contract" not in spec["usermeta"]
    assert _finding(audit_spec(spec, data=chart.data)).severity == "PASS"
    receipt = parse_group_cadence_contract(spec)
    assert receipt["observed_count"] == receipt["expected_cell_count"] == 6
    assert receipt["missing_preview"] == []


def test_wholly_missing_explicitly_expected_subgroup_is_detected():
    frame = _frame().query("channel == 'Paid'").copy()
    chart = _chart(frame)
    receipt = chart.to_vega_lite()["usermeta"]["group_cadence_contract"]
    assert receipt["missing_count"] == 3
    assert receipt["observed_count"] == 3
    assert receipt["missing_preview"] == [
        {"date": "2026-10-05", "group": "Organic"},
        {"date": "2026-10-12", "group": "Organic"},
        {"date": "2026-10-19", "group": "Organic"},
    ]


def test_declared_start_end_detects_both_edge_periods():
    chart = _chart(cadence_expected_start="2026-09-28", cadence_expected_end="2026-10-26")
    receipt = chart.to_vega_lite()["usermeta"]["group_cadence_contract"]
    assert receipt["expected_period_count"] == 5
    assert receipt["expected_cell_count"] == 10
    assert receipt["missing_count"] == 5
    assert receipt["missing_preview"][0] == {"date": "2026-09-28", "group": "Paid"}
    assert receipt["missing_preview"][1] == {"date": "2026-09-28", "group": "Organic"}
    assert _finding(chart.audit()).severity == "WARN"


def test_missing_global_final_week_is_caught_when_end_declared():
    chart = _chart(cadence_expected_end="2026-10-26")
    receipt = chart.to_vega_lite()["usermeta"]["group_cadence_contract"]
    assert receipt["missing_count"] == 3
    assert receipt["missing_preview"][-1] == {"date": "2026-10-26", "group": "Organic"}


def test_single_observed_group_period_with_declared_inventory_is_not_trivially_complete():
    frame = pd.DataFrame({"week": ["2026-10-05"], "channel": ["Paid"], "sales": [1]})
    chart = _chart(frame, cadence_expected_end="2026-10-12")
    receipt = chart.to_vega_lite()["usermeta"]["group_cadence_contract"]
    assert receipt["expected_cell_count"] == 4
    assert receipt["missing_count"] == 3


def test_missing_preview_chronological_and_bounded_to_five():
    frame = pd.DataFrame({"week": ["2026-10-05"], "channel": ["Paid"], "sales": [1]})
    chart = _chart(
        frame, cadence_expected_groups=["Paid", "Organic", "Partner"],
        cadence_expected_start="2026-09-28", cadence_expected_end="2026-10-26",
    )
    receipt = chart.to_vega_lite()["usermeta"]["group_cadence_contract"]
    assert receipt["missing_count"] == 14
    assert len(receipt["missing_preview"]) == 5
    assert receipt["missing_preview"][:3] == [
        {"date": "2026-09-28", "group": "Paid"},
        {"date": "2026-09-28", "group": "Organic"},
        {"date": "2026-09-28", "group": "Partner"},
    ]


def test_records_row_order_does_not_change_receipt():
    original = _chart().to_vega_lite()["usermeta"]["group_cadence_contract"]
    shuffled = _chart(_frame().iloc[::-1].reset_index(drop=True))
    receipt = shuffled.to_vega_lite()["usermeta"]["group_cadence_contract"]
    assert receipt == original


def test_daily_grid_with_one_group_gap():
    frame = pd.DataFrame({
        "week": ["2026-10-01", "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-03"],
        "channel": ["Paid", "Organic", "Paid", "Paid", "Organic"],
        "sales": [1, 2, 3, 4, 5],
    })
    chart = _chart(frame, cadence_frequency="daily")
    assert _finding(chart.audit()).severity == "WARN"
    assert _chart(frame, cadence_frequency="daily").to_vega_lite()[
        "usermeta"]["group_cadence_contract"]["missing_preview"] == [
        {"date": "2026-10-02", "group": "Organic"},
    ]


def test_monthly_grid_uses_calendar_firsts_in_leap_year():
    frame = pd.DataFrame({
        "week": ["2024-01-01", "2024-01-01", "2024-02-01", "2024-03-01", "2024-03-01"],
        "channel": ["Paid", "Organic", "Paid", "Paid", "Organic"],
        "sales": [1, 2, 3, 4, 5],
    })
    receipt = _chart(frame, cadence_frequency="monthly").to_vega_lite()["usermeta"]["group_cadence_contract"]
    assert receipt["expected_period_count"] == 3
    assert receipt["missing_preview"] == [{"date": "2024-02-01", "group": "Organic"}]


def test_valid_zero_metric_value_is_a_present_cell_not_a_missing_cell():
    frame = _frame()
    frame.loc[(frame.week == "2026-10-05") & (frame.channel == "Organic"), "sales"] = 0
    receipt = _chart(frame).to_vega_lite()["usermeta"]["group_cadence_contract"]
    assert receipt["missing_count"] == 1
    assert receipt["observed_count"] == 5


@pytest.mark.parametrize("overrides", [
    {"cadence_expected_groups": []},
    {"cadence_expected_groups": ["Paid", "Paid"]},
    {"cadence_expected_groups": ["Paid", ""]},
    {"cadence_expected_groups": ["Paid", 12]},
    {"cadence_expected_groups": "Paid"},
    {"cadence_expected_groups": ["Paid", "Organic"], "group": None},
    {"cadence_expected_groups": ["Paid", "Organic"], "group": "week"},
    {"cadence_frequency": "yearly"},
    {"cadence_frequency": None},
    {"cadence_require_complete": None},
    {"cadence_require_complete": 1},
    {"cadence_expected_start": "2026/10/05"},
    {"cadence_expected_end": "2026-10-20"},
    {"cadence_expected_start": "2026-10-26"},
    {"cadence_expected_end": "2026-10-12"},
    {"cadence_expected_start": "2026-10-26", "cadence_expected_end": "2026-10-05"},
])
def test_invalid_group_declarations_are_fail_closed(overrides):
    chart = _chart(**overrides)
    assert _finding(chart.audit(), "contract.trend.cadence_groups").severity in ("PASS", "FAIL")
    assert chart.audit().verdict == "BLOCK"
    with pytest.raises(ValueError):
        chart.to_vega_lite()


@pytest.mark.parametrize("mutation", [
    lambda f: f.loc.__setitem__(1, ["2026-10-05", "Paid", 50]),
    lambda f: f.loc.__setitem__(1, ["2026-10-06", "Organic", 50]),
    lambda f: f.loc.__setitem__(1, ["2026/10/05", "Organic", 50]),
    lambda f: f.loc.__setitem__(1, ["2026-10-05", "Unknown", 50]),
    lambda f: f.loc.__setitem__(1, ["2026-10-05", None, 50]),
])
def test_duplicate_offgrid_noncanonical_undeclared_or_null_group_fails(mutation):
    frame = _frame()
    mutation(frame)
    assert _finding(_chart(frame).audit(), "data.trend.cadence_groups_evidence").severity == "FAIL"
    with pytest.raises(ValueError):
        _chart(frame).to_vega_lite()


def test_missing_group_column_fails_source_validation():
    frame = _frame().drop(columns="channel")
    assert _finding(_chart(frame).audit(), "data.trend.cadence_groups_evidence").severity == "FAIL"


def test_empty_source_fails_evidence():
    assert _finding(_chart(_frame().iloc[:0]).audit(), "data.trend.cadence_groups_evidence").severity == "FAIL"


def test_monthly_source_or_boundary_cannot_be_mid_month():
    frame = pd.DataFrame({"week": ["2024-02-15"], "channel": ["Paid"], "sales": [2]})
    assert _finding(_chart(frame, cadence_frequency="monthly").audit(),
                    "data.trend.cadence_groups_evidence").severity == "FAIL"
    frame.loc[0, "week"] = "2024-02-01"
    assert _finding(_chart(frame, cadence_frequency="monthly", cadence_expected_start="2024-01-15").audit(),
                    "contract.trend.cadence_groups").severity == "FAIL"


def test_cell_cap_prevents_unbounded_cross_product():
    chart = _chart(
        cadence_frequency="daily", cadence_expected_start="1900-01-01",
        cadence_expected_groups=["Paid", "Organic"],
    )
    assert _finding(chart.audit(), "data.trend.cadence_groups_evidence").severity == "FAIL"


@pytest.mark.parametrize("key,bad", [
    ("missing_count", 0),
    ("observed_count", 6),
    ("expected_period_count", 5),
    ("expected_cell_count", 7),
    ("missing_preview", [{"date": "2026-10-12", "group": "Organic"}]),
])
def test_stale_or_tampered_receipt_never_passes(key, bad):
    chart = _chart()
    spec = deepcopy(chart.to_vega_lite())
    spec["usermeta"]["group_cadence_contract"][key] = bad
    report = audit_spec(spec, data=chart.data)
    assert report.verdict == "BLOCK"
    assert any(x.rule_id in ("contract.trend.cadence_groups", "data.trend.cadence_groups_evidence")
               and x.severity == "FAIL" for x in report.findings)


def test_external_data_mutation_is_detected():
    chart = _chart()
    spec = chart.to_vega_lite()
    changed = pd.concat([
        _frame(),
        pd.DataFrame({"week": ["2026-10-19"], "channel": ["Organic"], "sales": [60]}),
    ], ignore_index=True)
    assert _finding(audit_spec(spec, data=changed), "data.trend.cadence_groups_evidence").severity == "FAIL"


def test_external_without_evidence_fails_closed():
    chart = _chart()
    spec = deepcopy(chart.to_vega_lite())
    spec.pop("data", None)
    spec.pop("datasets", None)
    assert _finding(audit_spec(spec), "data.trend.cadence_groups_evidence").severity == "FAIL"


@pytest.mark.parametrize("mutation", [
    lambda spec: spec["encoding"]["color"].update(field="other"),
    lambda spec: spec["encoding"]["color"].update(type="quantitative"),
    lambda spec: spec.update(mark="bar"),
    lambda spec: spec.update(transform=[{"filter": "datum.sales > 50"}]),
    lambda spec: spec["encoding"]["y"].update(aggregate="sum"),
])
def test_detached_or_transformed_external_spec_fails_closed(mutation):
    chart = _chart()
    spec = deepcopy(chart.to_vega_lite())
    mutation(spec)
    assert _finding(audit_spec(spec, data=chart.data), "contract.trend.cadence_groups").severity == "FAIL"


def test_group_contract_requires_visible_color():
    chart = _chart()
    spec = deepcopy(chart.to_vega_lite())
    spec["encoding"].pop("color")
    assert _finding(audit_spec(spec, data=chart.data), "contract.trend.cadence_groups").severity == "FAIL"


def test_external_contract_extra_key_is_rejected():
    chart = _chart()
    spec = deepcopy(chart.to_vega_lite())
    spec["usermeta"]["group_cadence_contract"]["ignored"] = 42
    assert _finding(audit_spec(spec, data=chart.data), "contract.trend.cadence_groups").severity == "FAIL"


def test_first_party_with_group_but_no_inventory_requires_explicit_opt_in():
    chart = _chart(cadence_expected_groups=None)
    assert _finding(chart.audit(), "contract.trend.cadence").severity == "FAIL"


def test_grouped_plot_without_cadence_remains_supported():
    chart = _chart(
        cadence_expected_groups=None, cadence_frequency=None,
        cadence_require_complete=None, cadence_expected_start=None, cadence_expected_end=None,
    )
    assert not any("cadence" in finding.rule_id for finding in chart.audit().findings)
    spec = chart.to_vega_lite()
    assert spec["encoding"]["color"]["field"] == "channel"
    assert "group_cadence_contract" not in spec["usermeta"]


def test_existing_single_series_cadence_receipt_unchanged():
    chart = Chart.trend(
        data=pd.DataFrame({
            "week": ["2026-10-05", "2026-10-12", "2026-10-19"],
            "sales": [100, 110, 120],
        }),
        x="week", y="sales", claim="Weekly sales over observed dates.",
        source="synthetic.single_series", unit="systems",
        cadence_frequency="weekly", cadence_require_complete=False,
    )
    spec = chart.to_vega_lite()
    assert spec["usermeta"]["cadence_contract"]["version"] == 1
    assert "group_cadence_contract" not in spec["usermeta"]


def test_auditing_does_not_mutate_original_evidence():
    chart = _chart()
    saved = chart.data.copy(deep=True)
    chart.audit()
    chart.to_vega_lite()
    pd.testing.assert_frame_equal(saved, chart.data)


def test_cli_missing_organic_week_trap_blocks(capsys):
    code = main([
        "audit", "spec", str(TRAPS / "missing_subgroup_week.vl.json"),
        "--data", str(TRAPS / "missing_subgroup_week.csv"),
        "--claim", (TRAPS / "missing_subgroup_week.claim.txt").read_text().strip(),
    ])
    output = capsys.readouterr().out
    assert code == 1
    assert "Verdict: BLOCK" in output
    assert "PASS contract.trend.cadence_groups" in output
    assert "PASS data.trend.cadence_groups_evidence" in output
    assert "FAIL data.trend.cadence.groups:" in output
    assert "Organic @ 2026-10-19" in output
