"""Explicit expected-window boundaries extend v1 cadence without breaking old receipts."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from chart_contract import Chart, audit_spec
from chart_contract.cadence import build_cadence_receipt, parse_cadence_contract
from chart_contract.cli import main


TRAPS = Path(__file__).resolve().parents[1] / "examples" / "traps"


def _find(report, rule):
    return next(item for item in report.findings if item.rule_id == rule)


def _frame(dates=None):
    dates = dates if dates is not None else ["2026-10-05", "2026-10-12", "2026-10-19"]
    return pd.DataFrame({"week": dates, "sales": list(range(100, 100 + len(dates)))})


def _chart(frame=None, **overrides):
    kwargs = dict(
        data=_frame() if frame is None else frame,
        x="week", y="sales",
        claim="Recorded weekly sales for these reporting weeks.",
        source="synthetic.report_window", unit="systems", title="Weekly sales report",
        cadence_frequency="weekly", cadence_require_complete=False,
    )
    kwargs.update(overrides)
    return Chart.trend(**kwargs)


def test_v1_legacy_receipt_unchanged_and_no_boundary_findings():
    chart = _chart()
    receipt = chart.to_vega_lite()["usermeta"]["cadence_contract"]
    assert receipt == {
        "version": 1, "date_field": "week", "frequency": "weekly",
        "require_complete": False, "start_date": "2026-10-05",
        "end_date": "2026-10-19", "observed_count": 3,
        "expected_count": 3, "missing_count": 0, "missing_preview": [],
    }
    assert not any("cadence.boundaries" in f.rule_id for f in chart.audit().findings)
    spec_report = audit_spec(chart.to_vega_lite(), data=chart.data)
    assert _find(spec_report, "data.trend.cadence_evidence").severity == "PASS"
    assert not any("cadence.boundaries" in f.rule_id for f in spec_report.findings)


def test_trailing_week_warns_without_affecting_internal_cadence():
    chart = _chart(cadence_expected_end="2026-10-26")
    report = chart.audit()
    assert _find(report, "data.trend.cadence").severity == "PASS"
    assert _find(report, "data.trend.cadence.boundaries").severity == "WARN"
    assert report.verdict == "REVIEW"
    receipt = chart.to_vega_lite()["usermeta"]["cadence_contract"]
    assert receipt["version"] == 2
    assert receipt["expected_start"] is None
    assert receipt["expected_end"] == "2026-10-26"
    assert receipt["expected_count"] == 3
    assert receipt["expected_window_count"] == 4
    assert receipt["leading_missing_count"] == 0
    assert receipt["trailing_missing_count"] == 1
    assert receipt["boundary_missing_preview"] == ["2026-10-26"]
    spec_report = audit_spec(chart.to_vega_lite(), data=chart.data)
    assert _find(spec_report, "data.trend.cadence_evidence").severity == "PASS"
    assert _find(spec_report, "data.trend.cadence").severity == "PASS"
    assert _find(spec_report, "data.trend.cadence.boundaries").severity == "WARN"


def test_require_complete_blocks_trailing_week_and_first_party_render():
    chart = _chart(cadence_expected_end="2026-10-26", cadence_require_complete=True)
    assert chart.audit().verdict == "BLOCK"
    assert _find(chart.audit(), "data.trend.cadence.boundaries").severity == "FAIL"
    with pytest.raises(ValueError, match="missing cadence periods"):
        chart.to_vega_lite()


def test_leading_week_and_both_edges_are_independent():
    chart = _chart(
        cadence_expected_start="2026-09-28",
        cadence_expected_end="2026-10-26",
    )
    receipt = chart.to_vega_lite()["usermeta"]["cadence_contract"]
    assert receipt["leading_missing_count"] == 1
    assert receipt["trailing_missing_count"] == 1
    assert receipt["expected_window_count"] == 5
    assert receipt["boundary_missing_preview"] == ["2026-09-28", "2026-10-26"]
    assert _find(chart.audit(), "data.trend.cadence.boundaries").severity == "WARN"


def test_one_sided_leading_window_without_end_is_supported():
    chart = _chart(cadence_expected_start="2026-09-28")
    receipt = chart.to_vega_lite()["usermeta"]["cadence_contract"]
    assert receipt["expected_end"] is None
    assert receipt["leading_missing_count"] == 1
    assert receipt["trailing_missing_count"] == 0


def test_complete_expected_range_is_ready():
    chart = _chart(
        cadence_expected_start="2026-10-05", cadence_expected_end="2026-10-19",
        cadence_require_complete=True,
    )
    assert chart.audit().verdict == "READY"
    receipt = chart.to_vega_lite()["usermeta"]["cadence_contract"]
    assert receipt["expected_window_count"] == receipt["expected_count"] == 3
    assert _find(audit_spec(chart.to_vega_lite(), data=chart.data),
                 "data.trend.cadence.boundaries").severity == "PASS"


def test_internal_and_edge_gaps_are_reported_separately():
    frame = _frame(["2026-10-05", "2026-10-19"])
    chart = _chart(frame, cadence_expected_start="2026-09-28",
                   cadence_expected_end="2026-10-26")
    receipt = chart.to_vega_lite()["usermeta"]["cadence_contract"]
    assert receipt["missing_preview"] == ["2026-10-12"]
    assert receipt["missing_count"] == 1
    assert receipt["leading_missing_count"] == 1
    assert receipt["trailing_missing_count"] == 1
    assert receipt["expected_window_count"] == 5
    report = chart.audit()
    assert _find(report, "data.trend.cadence").severity == "WARN"
    assert _find(report, "data.trend.cadence.boundaries").severity == "WARN"


def test_monthly_calendar_edges_including_leap_year():
    frame = _frame(["2024-02-01", "2024-03-01", "2024-04-01"])
    chart = _chart(frame, cadence_frequency="monthly",
                   cadence_expected_start="2024-01-01",
                   cadence_expected_end="2024-05-01")
    receipt = chart.to_vega_lite()["usermeta"]["cadence_contract"]
    assert receipt["leading_missing_count"] == 1
    assert receipt["trailing_missing_count"] == 1
    assert receipt["boundary_missing_preview"] == ["2024-01-01", "2024-05-01"]
    assert receipt["expected_window_count"] == 5


def test_daily_edge_gaps_and_reordered_rows():
    frame = _frame(["2026-10-06", "2026-10-04", "2026-10-05"])
    chart = _chart(frame, cadence_frequency="daily",
                   cadence_expected_start="2026-10-03",
                   cadence_expected_end="2026-10-08")
    receipt = chart.to_vega_lite()["usermeta"]["cadence_contract"]
    assert receipt["start_date"] == "2026-10-04"
    assert receipt["end_date"] == "2026-10-06"
    assert receipt["leading_missing_count"] == 1
    assert receipt["trailing_missing_count"] == 2
    assert receipt["boundary_missing_preview"] == ["2026-10-03", "2026-10-07", "2026-10-08"]


@pytest.mark.parametrize("overrides", [
    {"cadence_expected_end": "2026-10-27"},
    {"cadence_expected_start": "2026-10-04"},
    {"cadence_expected_start": "2026-10-12"},
    {"cadence_expected_end": "2026-10-12"},
    {"cadence_expected_start": "2026-10-26", "cadence_expected_end": "2026-10-05"},
])
def test_offgrid_or_outside_window_is_rejected_without_guessing(overrides):
    chart = _chart(**overrides)
    report = chart.audit()
    assert report.verdict == "BLOCK"
    assert any(f.rule_id in {"contract.trend.cadence", "data.trend.cadence_evidence"}
               and f.severity == "FAIL" for f in report.findings)
    with pytest.raises(ValueError):
        chart.to_vega_lite()


@pytest.mark.parametrize("overrides", [
    {"cadence_expected_start": ""},
    {"cadence_expected_end": "not-a-date"},
    {"cadence_expected_end": "2026-10-26T00:00:00"},
    {"cadence_expected_end": 20261026},
    {"cadence_expected_end": "2026-02-30"},
    {"cadence_frequency": None, "cadence_expected_end": "2026-10-26"},
    {"cadence_require_complete": None, "cadence_expected_end": "2026-10-26"},
])
def test_malformed_boundary_declaration_fails_closed(overrides):
    chart = _chart(**overrides)
    assert _find(chart.audit(), "contract.trend.cadence").severity == "FAIL"
    with pytest.raises(ValueError):
        chart.to_vega_lite()


def test_monthly_boundary_must_be_calendar_first():
    frame = _frame(["2024-02-01", "2024-03-01", "2024-04-01"])
    chart = _chart(frame, cadence_frequency="monthly", cadence_expected_start="2024-01-31")
    assert _find(chart.audit(), "contract.trend.cadence").severity == "FAIL"


@pytest.mark.parametrize("key,bad", [
    ("expected_window_count", 1),
    ("leading_missing_count", 2),
    ("trailing_missing_count", 0),
    ("boundary_missing_preview", ["2026-10-19"]),
])
def test_stale_boundary_receipts_fail_even_if_internal_receipts_match(key, bad):
    chart = _chart(cadence_expected_end="2026-10-26")
    spec = deepcopy(chart.to_vega_lite())
    spec["usermeta"]["cadence_contract"][key] = bad
    report = audit_spec(spec, data=chart.data)
    assert report.verdict == "BLOCK"
    assert any(f.rule_id in {"data.trend.cadence_evidence", "contract.trend.cadence"}
               and f.severity == "FAIL" for f in report.findings)


def test_missing_source_evidence_fails_closed():
    chart = _chart(cadence_expected_end="2026-10-26")
    spec = deepcopy(chart.to_vega_lite())
    spec.pop("data", None)
    spec.pop("datasets", None)
    report = audit_spec(spec, data=None)
    assert _find(report, "data.trend.cadence_evidence").severity == "FAIL"


def test_v1_spec_with_v2_keys_rejected_not_upgraded_implicitly():
    chart = _chart()
    spec = chart.to_vega_lite()
    spec["usermeta"]["cadence_contract"]["expected_end"] = "2026-10-26"
    assert _find(audit_spec(spec, data=chart.data),
                 "contract.trend.cadence").severity == "FAIL"


def test_v2_contract_with_removed_field_rejected():
    chart = _chart(cadence_expected_end="2026-10-26")
    spec = chart.to_vega_lite()
    del spec["usermeta"]["cadence_contract"]["expected_start"]
    assert _find(audit_spec(spec, data=chart.data),
                 "contract.trend.cadence").severity == "FAIL"


def test_v2_without_any_declared_boundary_is_invalid():
    chart = _chart(cadence_expected_end="2026-10-26")
    spec = chart.to_vega_lite()
    spec["usermeta"]["cadence_contract"]["expected_end"] = None
    assert _find(audit_spec(spec, data=chart.data),
                 "contract.trend.cadence").severity == "FAIL"


def test_max_window_cap_applies_to_declared_edges_not_just_observed_span():
    chart = _chart(cadence_frequency="daily", cadence_expected_start="1970-01-01")
    assert _find(chart.audit(), "data.trend.cadence_evidence").severity == "FAIL"


def test_no_cadence_option_stays_legacy():
    chart = _chart(cadence_frequency=None, cadence_require_complete=None)
    assert "cadence_contract" not in chart.to_vega_lite()["usermeta"]
    assert not any("cadence" in f.rule_id for f in chart.audit().findings)


def test_cli_trailing_week_fixture_has_passed_internal_check(capsys):
    code = main([
        "audit", "spec", str(TRAPS / "missing_trailing_week.vl.json"),
        "--data", str(TRAPS / "missing_trailing_week.csv"),
        "--claim", (TRAPS / "missing_trailing_week.claim.txt").read_text().strip(),
    ])
    output = capsys.readouterr().out
    assert code == 1
    assert "Verdict: BLOCK" in output
    assert "PASS data.trend.cadence_evidence" in output
    assert "PASS data.trend.cadence:" in output
    assert "FAIL data.trend.cadence.boundaries" in output
    assert "2026-10-26" in output
