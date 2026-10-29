"""Deterministic data-freshness and source-finalization audit regressions."""

from __future__ import annotations

from copy import deepcopy

import pandas as pd
import pytest

from chart_contract import Chart, audit_spec
from chart_contract.freshness import parse_freshness_contract


def _finding(report, rule):
    return next(item for item in report.findings if item.rule_id == rule)


def _frame():
    return pd.DataFrame({
        "period": ["W1", "W2"],
        "sales": [100.0, 110.0],
        "observation_date": ["2026-10-27", "2026-10-28"],
    })


def _chart(frame=None, **overrides):
    fields = dict(
        data=_frame() if frame is None else frame,
        x="period", y="sales",
        claim="Recorded sales totals are shown for two reporting weeks.",
        source="synthetic.sales", unit="systems", title="Sales by reporting week",
        freshness_audit_date="2026-10-29",
        freshness_observation_date_field="observation_date",
        freshness_finalized_through="2026-10-28",
        freshness_max_age_days=7,
        freshness_require_finalized=True,
    )
    fields.update(overrides)
    return Chart.trend(**fields)


def test_freshness_ready_and_first_party_receipts():
    chart = _chart()
    report = chart.audit()
    for rule in (
        "contract.freshness.declared", "data.freshness.evidence",
        "data.freshness.age", "data.freshness.finalization",
    ):
        assert _finding(report, rule).severity == "PASS"
    assert report.verdict == "READY"
    saved = chart.to_vega_lite()["usermeta"]["freshness_contract"]
    assert saved == {
        "version": 1,
        "audit_date": "2026-10-29",
        "observation_date_field": "observation_date",
        "finalized_through": "2026-10-28",
        "max_age_days": 7,
        "require_finalized": True,
        "data_through": "2026-10-28",
        "row_count": 2,
    }


def test_external_spec_round_trip_verifies_receipts():
    chart = _chart()
    report = audit_spec(chart.to_vega_lite(), data=_frame(), claim=chart.claim)
    assert _finding(report, "data.freshness.evidence").severity == "PASS"
    assert _finding(report, "data.freshness.age").severity == "PASS"
    assert _finding(report, "data.freshness.finalization").severity == "PASS"


def test_stale_data_blocks_but_valid_receipts_pass():
    chart = _chart(freshness_max_age_days=0)
    report = chart.audit()
    assert report.verdict == "BLOCK"
    assert _finding(report, "data.freshness.evidence").severity == "PASS"
    assert "Stale data" in _finding(report, "data.freshness.age").message
    spec_report = audit_spec(chart.to_vega_lite(), data=_frame(), claim=chart.claim)
    assert _finding(spec_report, "data.freshness.age").severity == "FAIL"


def test_age_exactly_on_max_is_allowed():
    report = _chart(freshness_max_age_days=1).audit()
    assert _finding(report, "data.freshness.age").severity == "PASS"


def test_as_of_is_explicit_not_a_wall_clock_lookup():
    report = _chart(freshness_audit_date="2026-10-28", freshness_max_age_days=0).audit()
    assert _finding(report, "data.freshness.age").severity == "PASS"


def test_future_data_blocks():
    chart = _chart(freshness_audit_date="2026-10-27",
                   freshness_finalized_through="2026-10-27")
    report = chart.audit()
    assert "Future-dated" in _finding(report, "data.freshness.age").message
    assert _finding(report, "data.freshness.age").severity == "FAIL"


def test_preliminary_warns_when_finalized_not_required():
    report = _chart(freshness_finalized_through="2026-10-27",
                    freshness_require_finalized=False).audit()
    assert report.verdict == "REVIEW"
    assert _finding(report, "data.freshness.finalization").severity == "WARN"
    assert _finding(report, "data.freshness.age").severity == "PASS"


def test_preliminary_blocks_when_finalized_required():
    report = _chart(freshness_finalized_through="2026-10-27").audit()
    assert report.verdict == "BLOCK"
    assert _finding(report, "data.freshness.finalization").severity == "FAIL"


@pytest.mark.parametrize("override", [
    {"freshness_audit_date": None},
    {"freshness_audit_date": "2026/10/29"},
    {"freshness_audit_date": "2026-02-30"},
    {"freshness_audit_date": "2026-10-29T00:00:00"},
    {"freshness_observation_date_field": ""},
    {"freshness_max_age_days": -1},
    {"freshness_max_age_days": 1.0},
    {"freshness_max_age_days": True},
    {"freshness_require_finalized": "true"},
    {"freshness_finalized_through": None},
    {"freshness_finalized_through": "2026-10-30"},
])
def test_malformed_first_party_declaration_blocks(override):
    chart = _chart(**override)
    report = chart.audit()
    assert report.verdict == "BLOCK"
    assert _finding(report, "contract.freshness.declared").severity == "FAIL"
    with pytest.raises(ValueError):
        chart.to_vega_lite()


@pytest.mark.parametrize("dates", [
    ["2026-10-27", None],
    ["2026-10-27", "2026/10/28"],
    ["2026-10-27", "2026-10-28T01:00:00"],
    ["2026-10-27", "2026-02-30"],
])
def test_invalid_row_dates_block_and_renderer_refuses(dates):
    frame = _frame()
    frame["observation_date"] = dates
    chart = _chart(frame)
    assert _finding(chart.audit(), "data.freshness.evidence").severity == "FAIL"
    with pytest.raises(ValueError):
        chart.to_vega_lite()


def test_empty_or_missing_evidence_blocks():
    empty = _chart(_frame().iloc[0:0]).audit()
    assert _finding(empty, "data.freshness.evidence").severity == "FAIL"
    missing = _chart(_frame().drop(columns=["observation_date"])).audit()
    assert _finding(missing, "data.freshness.evidence").severity == "FAIL"


def test_spec_requires_reconstructable_evidence():
    chart = _chart()
    spec = deepcopy(chart.to_vega_lite())
    spec.pop("datasets", None)
    spec.pop("data", None)
    report = audit_spec(spec, data=None, claim=chart.claim)
    assert _finding(report, "data.freshness.evidence").severity == "FAIL"


@pytest.mark.parametrize(("receipt", "bad"), [
    ("data_through", "2026-10-27"),
    ("row_count", 3),
])
def test_stale_receipts_block_even_with_fresh_dates(receipt, bad):
    chart = _chart()
    spec = deepcopy(chart.to_vega_lite())
    spec["usermeta"]["freshness_contract"][receipt] = bad
    report = audit_spec(spec, data=_frame(), claim=chart.claim)
    assert _finding(report, "data.freshness.evidence").severity == "FAIL"
    assert "Stale freshness receipts" in _finding(report, "data.freshness.evidence").message


@pytest.mark.parametrize(("key", "bad"), [
    ("row_count", False),
    ("row_count", 0),
    ("data_through", "not-a-date"),
    ("require_finalized", 1),
    ("max_age_days", -1),
    ("audit_date", "2026/10/29"),
])
def test_malformed_spec_contract_fails_closed(key, bad):
    spec = deepcopy(_chart().to_vega_lite())
    spec["usermeta"]["freshness_contract"][key] = bad
    report = audit_spec(spec, data=_frame())
    assert _finding(report, "contract.freshness.declared").severity == "FAIL"


def test_extra_spec_contract_field_fails_closed():
    spec = deepcopy(_chart().to_vega_lite())
    spec["usermeta"]["freshness_contract"]["extra"] = "not supported"
    report = audit_spec(spec, data=_frame())
    assert _finding(report, "contract.freshness.declared").severity == "FAIL"


def test_removed_receipt_field_fails_closed():
    spec = deepcopy(_chart().to_vega_lite())
    del spec["usermeta"]["freshness_contract"]["row_count"]
    report = audit_spec(spec, data=_frame())
    assert _finding(report, "contract.freshness.declared").severity == "FAIL"


def test_legacy_chart_unchanged_without_opt_in():
    chart = _chart(
        freshness_audit_date=None,
        freshness_observation_date_field=None,
        freshness_finalized_through=None,
        freshness_max_age_days=None,
        freshness_require_finalized=None,
    )
    assert not any("freshness" in f.rule_id for f in chart.audit().findings)
    assert "freshness_contract" not in chart.to_vega_lite()["usermeta"]


def test_rank_and_compare_constructor_surface_accepts_freshness():
    arguments = {
        "freshness_audit_date": "2026-10-29",
        "freshness_observation_date_field": "observation_date",
        "freshness_finalized_through": "2026-10-28",
        "freshness_max_age_days": 7,
        "freshness_require_finalized": True,
    }
    for constructor in (Chart.rank, Chart.compare):
        chart = constructor(
            data=_frame(), x="period", y="sales",
            claim="Sales are shown across two periods.",
            source="synthetic.sales", unit="systems", **arguments,
        )
        assert _finding(chart.audit(), "data.freshness.age").severity == "PASS"
        assert parse_freshness_contract(chart.to_vega_lite())["data_through"] == "2026-10-28"


def test_latest_date_not_first_or_last_input_order():
    frame = _frame().iloc[::-1].reset_index(drop=True)
    assert _chart(frame).to_vega_lite()["usermeta"]["freshness_contract"]["data_through"] == "2026-10-28"
