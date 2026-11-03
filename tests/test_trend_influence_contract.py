"""Adversarial leave-one-out trend influence sensitivity regressions."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from chart_contract import Chart, audit_spec
from chart_contract.cli import main
from chart_contract.trend_influence import build_influence_receipt

ROOT = Path(__file__).resolve().parents[1]
TRAPS = ROOT / "examples" / "traps"


def finding(report, rule):
    return next(item for item in report.findings if item.rule_id == rule)


def frame(y=None, x=None):
    return pd.DataFrame({
        "week": x if x is not None else [
            "2026-09-07", "2026-09-14", "2026-09-21",
            "2026-09-28", "2026-10-05", "2026-10-12",
        ],
        "sales": y if y is not None else [10, 9, 8, 7, 6, 30],
    })


def chart(data=None, **overrides):
    kwargs = dict(
        data=frame() if data is None else data,
        x="week", y="sales", trend_influence=True,
        claim="Reported weekly sales by date.",
        title="Reported weekly sales", source="synthetic.influence",
        unit="systems",
    )
    kwargs.update(overrides)
    return Chart.trend(**kwargs)


def test_outlier_reverses_slope_and_warns():
    c = chart()
    report = c.audit()
    assert report.verdict == "REVIEW"
    assert finding(report, "contract.trend.influence").severity == "PASS"
    assert finding(report, "data.trend.influence_evidence").severity == "PASS"
    flag = finding(report, "stat.trend.influence")
    assert flag.severity == "WARN"
    assert "2026-10-12" in flag.message
    receipt = c.to_vega_lite()["usermeta"]["trend_influence_contract"]
    assert receipt["row_count"] == 6
    assert receipt["x_kind"] == "date"
    assert receipt["full_slope"] > 0
    assert receipt["loo_min_slope"] < 0
    assert receipt["reversal_count"] >= 1
    assert "2026-10-12" in receipt["reversal_preview"]
    spec_report = audit_spec(c.to_vega_lite(), data=c.data, claim=c.claim)
    assert finding(spec_report, "stat.trend.influence").severity == "WARN"
    assert finding(spec_report, "data.trend.influence_evidence").severity == "PASS"


def test_no_direction_reversal_passes():
    for y in ([10, 11, 12, 13, 14, 15], [15, 14, 13, 12, 11, 10]):
        c = chart(frame(y=y))
        report = c.audit()
        assert finding(report, "stat.trend.influence").severity == "PASS"
        receipt = c.to_vega_lite()["usermeta"]["trend_influence_contract"]
        assert receipt["reversal_count"] == 0


def test_flat_full_slope_does_not_manufacture_reversal():
    c = chart(frame(y=[1, 2, 3, 3, 2, 1]))
    receipt = c.to_vega_lite()["usermeta"]["trend_influence_contract"]
    assert abs(receipt["full_slope"]) <= receipt["flat_tolerance"]
    assert receipt["reversal_count"] == 0
    assert finding(c.audit(), "stat.trend.influence").severity == "PASS"


def test_numeric_x_uses_true_spacing_and_is_order_independent():
    f = frame(x=[0, 1, 2, 3, 4, 5])
    c = chart(f)
    assert c.to_vega_lite()["usermeta"]["trend_influence_contract"]["x_kind"] == "numeric"
    assert finding(c.audit(), "stat.trend.influence").severity == "WARN"
    reversed_chart = chart(f.iloc[::-1].reset_index(drop=True))
    a = c.to_vega_lite()["usermeta"]["trend_influence_contract"]
    b = reversed_chart.to_vega_lite()["usermeta"]["trend_influence_contract"]
    assert a == b


def test_nonuniform_numeric_x_supported_without_imputing_regular_cadence():
    c = chart(frame(x=[0, 1, 2, 3, 4, 100]))
    assert finding(c.audit(), "data.trend.influence_evidence").severity == "PASS"


def test_negative_numeric_values_can_be_audited():
    c = chart(frame(x=[-5, -4, -3, -2, -1, 0], y=[-10, -9, -8, -7, -6, 30]))
    assert finding(c.audit(), "data.trend.influence_evidence").severity == "PASS"


@pytest.mark.parametrize("bad", ["yes", 1, 0, [], {}, "false"])
def test_opt_in_must_be_literal_boolean(bad):
    c = chart(trend_influence=bad)
    assert finding(c.audit(), "contract.trend.influence").severity == "FAIL"
    with pytest.raises(ValueError, match="trend_influence"):
        c.to_vega_lite()


def test_false_and_none_do_not_emit_new_rules():
    for enabled in (None, False):
        c = chart(trend_influence=enabled)
        assert not any("influence" in f.rule_id for f in c.audit().findings)
        assert "trend_influence_contract" not in c.to_vega_lite()["usermeta"]


@pytest.mark.parametrize(("x", "y"), [
    ([1, 1, 2, 3, 4, 5], [10, 9, 8, 7, 6, 30]),
    (["2026-09-07", "2026-09-07", "2026-09-21", "2026-09-28", "2026-10-05", "2026-10-12"], [10, 9, 8, 7, 6, 30]),
    ([1, 2, 3, 4, 5, float("inf")], [10, 9, 8, 7, 6, 30]),
    ([1, 2, 3, 4, 5, True], [10, 9, 8, 7, 6, 30]),
    ([1, 2, 3, 4, 5, "6"], [10, 9, 8, 7, 6, 30]),
    (["2026-09-07", "2026-09-14", "2026-09-21", "2026-09-28", "2026-10-05", "2026/10/12"], [10, 9, 8, 7, 6, 30]),
    ([0, 1, 2, 3, 4, 5], [10, 9, 8, None, 6, 30]),
    ([0, 1, 2, 3, 4, 5], [10, 9, 8, float("nan"), 6, 30]),
    ([0, 1, 2, 3, 4, 5], [10, 9, 8, True, 6, 30]),
])
def test_invalid_source_evidence_blocks_and_renderer_refuses(x, y):
    c = chart(frame(x=x, y=y))
    assert finding(c.audit(), "data.trend.influence_evidence").severity == "FAIL"
    with pytest.raises((ValueError, OverflowError)):
        c.to_vega_lite()


def test_missing_columns_and_too_few_rows_block():
    for f in (frame().drop(columns=["sales"]), frame().drop(columns=["week"]), frame().iloc[:4]):
        assert finding(chart(f).audit(), "data.trend.influence_evidence").severity == "FAIL"


def test_too_many_rows_refused_without_quadratic_work():
    f = pd.DataFrame({"week": list(range(2001)), "sales": list(range(2001))})
    report = chart(f).audit()
    assert finding(report, "data.trend.influence_evidence").severity == "FAIL"
    assert "2000" in finding(report, "data.trend.influence_evidence").message


def test_missing_spec_source_fails_closed():
    c = chart()
    spec = deepcopy(c.to_vega_lite())
    spec.pop("data", None)
    spec.pop("datasets", None)
    report = audit_spec(spec, data=None)
    assert finding(report, "data.trend.influence_evidence").severity == "FAIL"


@pytest.mark.parametrize(("field", "bad"), [
    ("full_slope", 0.0), ("loo_min_slope", 0.0),
    ("reversal_count", 0), ("reversal_preview", []),
    ("row_count", 8),
])
def test_stale_receipt_is_rejected(field, bad):
    c = chart()
    spec = deepcopy(c.to_vega_lite())
    spec["usermeta"]["trend_influence_contract"][field] = bad
    report = audit_spec(spec, data=c.data)
    assert finding(report, "data.trend.influence_evidence").severity == "FAIL"


@pytest.mark.parametrize(("field", "bad"), [
    ("version", True), ("x_field", "other"), ("y_field", ""),
    ("row_count", False), ("flat_tolerance", -1),
    ("full_slope", float("inf")), ("reversal_count", -1),
    ("x_kind", "category"), ("reversal_preview", [12]),
])
def test_malformed_metadata_is_rejected(field, bad):
    c = chart()
    spec = deepcopy(c.to_vega_lite())
    spec["usermeta"]["trend_influence_contract"][field] = bad
    report = audit_spec(spec, data=c.data)
    assert finding(report, "contract.trend.influence").severity == "FAIL"


def test_extra_contract_field_rejected():
    c = chart()
    spec = deepcopy(c.to_vega_lite())
    spec["usermeta"]["trend_influence_contract"]["unknown"] = 1
    assert finding(audit_spec(spec, data=c.data), "contract.trend.influence").severity == "FAIL"


def test_source_mutation_invalidates_saved_influence_receipt():
    c = chart()
    spec = c.to_vega_lite()
    changed = c.data.copy()
    changed.loc[changed.index[-1], "sales"] = 25
    assert finding(audit_spec(spec, data=changed), "data.trend.influence_evidence").severity == "FAIL"


@pytest.mark.parametrize("edit", [
    lambda s: s["encoding"]["y"].update(field="invisible_metric"),
    lambda s: s.update(mark="bar"),
    lambda s: s.update(transform=[{"filter": "datum.sales > 0"}]),
    lambda s: s["encoding"]["y"].update(aggregate="sum"),
    lambda s: s["encoding"]["x"].update(timeUnit="month"),
])
def test_spec_requires_untransformed_visible_line(edit):
    c = chart()
    spec = deepcopy(c.to_vega_lite())
    edit(spec)
    report = audit_spec(spec, data=c.data)
    assert finding(report, "contract.trend.influence").severity == "FAIL"


def test_report_says_not_significance_or_causation():
    message = finding(chart().audit(), "stat.trend.influence").message
    assert "not statistical significance or causation" in message


def test_hero_cli_trap_review_and_warning_gated(capsys):
    args = [
        "audit", "spec", str(TRAPS / "influential_weekly_sales.vl.json"),
        "--data", str(TRAPS / "influential_weekly_sales.csv"),
        "--claim", (TRAPS / "influential_weekly_sales.claim.txt").read_text().strip(),
    ]
    assert main(args) == 0
    text = capsys.readouterr().out
    assert "Verdict: REVIEW" in text
    assert "WARN stat.trend.influence" in text
    assert "2026-10-12" in text
    assert main(args + ["--warnings-as-errors"]) == 1
