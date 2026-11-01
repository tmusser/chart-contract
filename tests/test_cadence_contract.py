"""Regressions for explicit daily/weekly/monthly cadence and missing periods."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from chart_contract import Chart, audit_spec
from chart_contract.cli import main
from chart_contract.cadence import build_cadence_receipt, parse_cadence_contract

TRAPS = Path(__file__).resolve().parents[1] / "examples" / "traps"


def _find(report, rule):
    return next(x for x in report.findings if x.rule_id == rule)


def _frame(dates=None):
    return pd.DataFrame({
        "date": dates or ["2026-10-05", "2026-10-12", "2026-10-19"],
        "sales": [100, 110, 120],
    })


def _chart(frame=None, **kwargs):
    args = dict(
        data=_frame() if frame is None else frame, x="date", y="sales",
        claim="Recorded weekly sales by week.", source="synthetic.weekly_sales",
        title="Weekly sales", unit="systems",
        cadence_frequency="weekly", cadence_require_complete=False,
    )
    args.update(kwargs)
    return Chart.trend(**args)


def test_complete_weekly_first_party_and_spec_roundtrip():
    chart = _chart()
    assert chart.audit().verdict == "READY"
    for rule in ("contract.trend.cadence", "data.trend.cadence_evidence", "data.trend.cadence"):
        assert _find(chart.audit(), rule).severity == "PASS"
    spec = chart.to_vega_lite()
    receipt = parse_cadence_contract(spec)
    assert receipt["frequency"] == "weekly"
    assert receipt["observed_count"] == receipt["expected_count"] == 3
    assert receipt["missing_count"] == 0
    assert receipt["missing_preview"] == []
    assert _find(audit_spec(spec, data=chart.data), "data.trend.cadence").severity == "PASS"


def test_missing_week_warns_and_receipt_recomputes():
    frame = _frame(["2026-10-05", "2026-10-19", "2026-10-26"])
    report = _chart(frame).audit()
    assert report.verdict == "REVIEW"
    finding = _find(report, "data.trend.cadence")
    assert finding.severity == "WARN"
    assert "2026-10-12" in finding.message
    receipt = _chart(frame).to_vega_lite()["usermeta"]["cadence_contract"]
    assert receipt["missing_count"] == 1
    assert receipt["observed_count"] == 3
    assert receipt["expected_count"] == 4
    assert receipt["missing_preview"] == ["2026-10-12"]
    assert _find(audit_spec(_chart(frame).to_vega_lite(), data=frame),
                 "data.trend.cadence").severity == "WARN"


def test_missing_week_blocks_when_complete_required_and_renderer_refuses():
    frame = _frame(["2026-10-05", "2026-10-19", "2026-10-26"])
    chart = _chart(frame, cadence_require_complete=True)
    assert _find(chart.audit(), "data.trend.cadence").severity == "FAIL"
    with pytest.raises(ValueError, match="missing cadence"):
        chart.to_vega_lite()


def test_daily_gap_and_unsorted_complete_dates():
    source = _frame(["2026-10-03", "2026-10-01", "2026-10-02"])
    receipt = build_cadence_receipt(source, {
        "version": 1, "date_field": "date", "frequency": "daily",
        "require_complete": True,
    })
    assert receipt["missing_count"] == 0
    bad = _frame(["2026-10-01", "2026-10-03", "2026-10-04"])
    assert _find(_chart(bad, cadence_frequency="daily").audit(),
                 "data.trend.cadence").severity == "WARN"


def test_monthly_calendar_gap_including_leap_year():
    frame = _frame(["2024-01-01", "2024-03-01", "2024-04-01"])
    receipt = _chart(frame, cadence_frequency="monthly").to_vega_lite()["usermeta"]["cadence_contract"]
    assert receipt["missing_preview"] == ["2024-02-01"]
    assert receipt["expected_count"] == 4


@pytest.mark.parametrize("dates,frequency", [
    (["2026-10-05", "2026-10-05", "2026-10-12"], "weekly"),
    (["2026-10-05", "2026-10-14", "2026-10-19"], "weekly"),
    (["2026-10-05", "2026-10-12", "2026-10-19"], "monthly"),
    (["2026-10-05", "bad", "2026-10-19"], "weekly"),
    (["2026-10-05", None, "2026-10-19"], "weekly"),
    (["2026-10-05", "2026-10-12T00:00:00", "2026-10-19"], "weekly"),
])
def test_invalid_dates_or_off_grid_block_and_renderer_refuses(dates, frequency):
    frame = _frame(dates)
    chart = _chart(frame, cadence_frequency=frequency)
    assert _find(chart.audit(), "data.trend.cadence_evidence").severity == "FAIL"
    with pytest.raises(ValueError):
        chart.to_vega_lite()


@pytest.mark.parametrize("frequency,required", [
    ("yearly", False), ("weekly", None), ("weekly", "false"),
    ("daily", 1), (None, False),
])
def test_partial_or_invalid_firstparty_declaration_blocks(frequency, required):
    chart = _chart(cadence_frequency=frequency, cadence_require_complete=required)
    assert _find(chart.audit(), "contract.trend.cadence").severity == "FAIL"
    with pytest.raises(ValueError):
        chart.to_vega_lite()


def test_missing_date_column_or_empty_frame_blocks():
    chart = _chart(_frame().drop(columns=["date"]))
    assert _find(chart.audit(), "data.trend.cadence_evidence").severity == "FAIL"
    chart = _chart(_frame().iloc[:0])
    assert _find(chart.audit(), "data.trend.cadence_evidence").severity == "FAIL"


def test_external_spec_receipts_mutation_is_fail_closed():
    chart = _chart()
    spec = deepcopy(chart.to_vega_lite())
    spec["usermeta"]["cadence_contract"]["missing_count"] = 5
    report = audit_spec(spec, data=chart.data)
    assert _find(report, "data.trend.cadence_evidence").severity == "FAIL"
    assert "Stale cadence receipts" in _find(report, "data.trend.cadence_evidence").message


@pytest.mark.parametrize("field,bad", [
    ("observed_count", True),
    ("frequency", "biweekly"),
    ("date_field", ""),
    ("start_date", "not a date"),
    ("require_complete", 0),
    ("missing_preview", ["2026/10/12"]),
    ("missing_count", -1),
])
def test_external_malformed_contract_is_fail_closed(field, bad):
    chart = _chart()
    spec = deepcopy(chart.to_vega_lite())
    spec["usermeta"]["cadence_contract"][field] = bad
    assert _find(audit_spec(spec, data=chart.data), "contract.trend.cadence").severity == "FAIL"


def test_external_contract_extra_field_is_rejected():
    chart = _chart()
    spec = deepcopy(chart.to_vega_lite())
    spec["usermeta"]["cadence_contract"]["mystery"] = 7
    assert _find(audit_spec(spec, data=chart.data), "contract.trend.cadence").severity == "FAIL"


def test_external_evidence_missing_fails_not_passes():
    chart = _chart()
    spec = deepcopy(chart.to_vega_lite())
    spec.pop("data", None)
    spec.pop("datasets", None)
    assert _find(audit_spec(spec, data=None), "data.trend.cadence_evidence").severity == "FAIL"


def test_external_binding_must_be_visible_line_x_and_quantitative_y():
    chart = _chart()
    spec = deepcopy(chart.to_vega_lite())
    spec["mark"] = "bar"
    assert _find(audit_spec(spec, data=chart.data), "contract.trend.cadence").severity == "FAIL"
    spec = deepcopy(chart.to_vega_lite())
    spec["encoding"]["x"]["field"] = "unrelated"
    assert _find(audit_spec(spec, data=chart.data), "contract.trend.cadence").severity == "FAIL"


def test_reordered_source_receipts_do_not_depend_on_row_order():
    chart = _chart(_frame().iloc[::-1].reset_index(drop=True))
    receipt = chart.to_vega_lite()["usermeta"]["cadence_contract"]
    assert receipt["start_date"] == "2026-10-05"
    assert receipt["end_date"] == "2026-10-19"
    assert receipt["missing_count"] == 0


def test_no_opt_in_preserves_legacy_chart_behavior():
    chart = _chart(cadence_frequency=None, cadence_require_complete=None)
    assert not any("cadence" in f.rule_id for f in chart.audit().findings)
    assert "cadence_contract" not in chart.to_vega_lite()["usermeta"]


def test_one_period_allowed_and_safety_limit_enforced():
    frame = pd.DataFrame({"date": ["2026-10-05"], "sales": [1]})
    receipt = build_cadence_receipt(frame, {
        "version": 1, "date_field": "date",
        "frequency": "weekly", "require_complete": False,
    })
    assert receipt["expected_count"] == 1
    long = _frame(["1900-01-01", "2026-01-01", "2026-10-19"])
    assert _find(_chart(long, cadence_frequency="daily").audit(),
                 "data.trend.cadence_evidence").severity == "FAIL"


def test_cli_omitted_week_trap_blocks_with_receipts_pass(capsys):
    code = main(["audit", "spec", str(TRAPS / "missing_weekly_sales.vl.json"),
                 "--data", str(TRAPS / "missing_weekly_sales.csv"),
                 "--claim", (TRAPS / "missing_weekly_sales.claim.txt").read_text().strip()])
    stdout = capsys.readouterr().out
    assert code == 1
    assert "Verdict: BLOCK" in stdout
    assert "data.trend.cadence_evidence" in stdout
    assert "FAIL data.trend.cadence" in stdout
    assert "2026-09-14" in stdout
