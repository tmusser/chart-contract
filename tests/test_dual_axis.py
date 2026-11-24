"""Adversarial checks for overlaid quantitative measures on independent y axes."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from chart_contract import Chart, audit_spec
from chart_contract.cli import main

RULE = "visual.dual_axis.review"
TRAPS = Path(__file__).resolve().parents[1] / "examples" / "traps"


def _data():
    return pd.DataFrame({
        "week": ["W1", "W2", "W3", "W4"],
        "ad_spend": [80, 100, 95, 120],
        "sales": [800, 850, 900, 950],
    })


def _layers():
    return [
        {
            "mark": "line",
            "encoding": {
                "x": {"field": "week", "type": "ordinal"},
                "y": {"field": "ad_spend", "type": "quantitative", "axis": {"title": "Ad spend ($)"}},
            },
        },
        {
            "mark": "line",
            "encoding": {
                "x": {"field": "week", "type": "ordinal"},
                "y": {"field": "sales", "type": "quantitative", "axis": {"title": "Systems sold"}},
            },
        },
    ]


def _spec(*, independent=True):
    spec = {
        "title": "Weekly advertising spend and system sales",
        "layer": _layers(),
        "usermeta": {
            "source": "synthetic.dual_axis",
            "unit": "USD and systems",
            "claim": "Recorded advertising spend and system sales by week.",
        },
    }
    if independent:
        spec["resolve"] = {"scale": {"y": "independent"}}
    return spec


def _findings(spec, data=None):
    report = audit_spec(spec, data=_data() if data is None else data)
    return [finding for finding in report.findings if finding.rule_id == RULE]


def test_two_independently_scaled_quantitative_metrics_warn():
    result = _findings(_spec())
    assert len(result) == 1
    assert result[0].severity == "WARN"
    assert result[0].field == "resolve.scale.y"
    assert "ad_spend" in result[0].message
    assert "sales" in result[0].message
    assert "correlation" in result[0].message


def test_shared_scale_layer_does_not_trigger():
    assert not _findings(_spec(independent=False))
    spec = _spec()
    spec["resolve"]["scale"]["y"] = "shared"
    assert not _findings(spec)


def test_independent_x_only_does_not_trigger():
    spec = _spec(independent=False)
    spec["resolve"] = {"scale": {"x": "independent"}}
    assert not _findings(spec)


def test_independent_axis_without_independent_scale_is_not_a_dual_scale():
    spec = _spec(independent=False)
    spec["resolve"] = {"axis": {"y": "independent"}}
    assert not _findings(spec)


def test_independent_color_scales_are_not_dual_y_axes():
    spec = _spec(independent=False)
    spec["resolve"] = {"scale": {"color": "independent"}}
    assert not _findings(spec)


def test_same_y_metric_line_plus_point_overlay_is_not_multi_measure():
    spec = _spec()
    spec["layer"][1]["encoding"]["y"]["field"] = "ad_spend"
    spec["layer"][1]["mark"] = "point"
    assert not _findings(spec)


def test_same_field_but_different_aggregation_is_distinct_measure():
    spec = _spec()
    spec["layer"][1]["encoding"]["y"]["field"] = "ad_spend"
    spec["layer"][0]["encoding"]["y"]["aggregate"] = "mean"
    spec["layer"][1]["encoding"]["y"]["aggregate"] = "sum"
    result = _findings(spec)
    assert len(result) == 1
    assert result[0].severity == "WARN"


def test_y2_range_does_not_count_as_a_second_axis():
    spec = _spec()
    spec["layer"] = [spec["layer"][0]]
    spec["layer"][0]["encoding"]["y2"] = {"field": "sales"}
    assert not _findings(spec)


def test_categorical_second_layer_is_not_an_independent_quant_axis():
    spec = _spec()
    spec["layer"][1]["encoding"]["y"]["type"] = "nominal"
    assert not _findings(spec)


def test_constant_horizontal_reference_line_is_not_a_second_measure():
    spec = _spec()
    spec["layer"][1]["encoding"]["y"] = {"datum": 800, "type": "quantitative"}
    assert not _findings(spec)


def test_root_level_inherited_x_and_child_y_detected():
    spec = _spec()
    spec["encoding"] = {"x": {"field": "week", "type": "ordinal"}}
    for child in spec["layer"]:
        del child["encoding"]["x"]
    assert _findings(spec)[0].severity == "WARN"


def test_root_level_y_inherited_by_one_child_detected():
    spec = _spec()
    spec["encoding"] = {
        "x": {"field": "week", "type": "ordinal"},
        "y": {"field": "sales", "type": "quantitative"},
    }
    del spec["layer"][1]["encoding"]["y"]
    assert _findings(spec)[0].severity == "WARN"


def test_concat_panels_do_not_trigger_just_because_their_scales_are_independent():
    spec = _spec()
    layers = spec.pop("layer")
    spec["hconcat"] = layers
    assert not _findings(spec)


def test_concat_with_nested_independent_overlay_warns_only_on_nested_view():
    spec = _spec()
    spec = {"hconcat": [
        {"mark": "line", "encoding": _layers()[0]["encoding"]},
        spec,
    ], "title": "Separate panels", "usermeta": _spec()["usermeta"]}
    findings = _findings(spec)
    assert len(findings) == 1
    assert findings[0].field == "hconcat[1].resolve.scale.y"


def test_nested_layer_groups_are_inspected_with_correct_field_paths():
    child = _spec()
    spec = {
        "layer": [child, {"mark": "point", "encoding": _layers()[0]["encoding"]}],
        "title": "Nested overlays",
        "usermeta": _spec()["usermeta"],
    }
    findings = _findings(spec)
    assert len(findings) == 1
    assert findings[0].field == "layer[0].resolve.scale.y"


def test_outer_and_inner_independent_overlays_have_independent_findings():
    child = _spec()
    spec = {
        "layer": [child, {"mark": "point", "encoding": _layers()[0]["encoding"]}],
        "resolve": {"scale": {"y": "independent"}},
        "title": "Nested dual axes",
        "usermeta": _spec()["usermeta"],
    }
    fields = [finding.field for finding in _findings(spec)]
    assert fields == ["resolve.scale.y", "layer[0].resolve.scale.y"]


def test_non_layer_or_malformed_resolution_never_reports_a_dual_axis():
    for resolve in (None, "independent", {}, {"scale": "independent"}, {"scale": {"y": False}}):
        spec = _spec(independent=False)
        if resolve is not None:
            spec["resolve"] = resolve
        assert not _findings(spec)


def test_only_one_independent_y_mark_does_not_warn():
    spec = _spec()
    spec["layer"] = spec["layer"][:1]
    assert not _findings(spec)


def test_all_quantitative_axes_are_separate_without_mutating_data_or_spec():
    spec = _spec()
    data = _data()
    before = deepcopy(spec)
    original = data.copy(deep=True)
    _findings(spec, data)
    assert spec == before
    pd.testing.assert_frame_equal(data, original)


def test_explicit_domain_authorization_does_not_suppress_review():
    spec = _spec()
    for index, child in enumerate(spec["layer"]):
        child["encoding"]["y"]["scale"] = {
            "domain": [0, 1000 if index else 130],
        }
    spec["usermeta"]["user_requested_scale_override"] = True
    report = audit_spec(spec, data=_data())
    items = [f for f in report.findings if f.rule_id == RULE]
    assert items and items[0].severity == "WARN"


def test_ordinary_first_party_trend_is_not_flagged():
    chart = Chart.trend(
        data=pd.DataFrame({"week": ["W1", "W2", "W3"], "sales": [1, 2, 3]}),
        x="week", y="sales", claim="Recorded sales by week.",
        source="synthetic.single_axis", title="Sales by week", unit="systems",
    )
    assert not _findings(chart.to_vega_lite(), data=chart.data)


def test_cli_synthetic_dual_axis_trap_reviews_but_does_not_block(capsys):
    args = [
        "audit", "spec", str(TRAPS / "dual_axis_spend_sales.vl.json"),
        "--data", str(TRAPS / "dual_axis_spend_sales.csv"),
        "--claim", (TRAPS / "dual_axis_spend_sales.claim.txt").read_text().strip(),
    ]
    code = main(args)
    output = capsys.readouterr().out
    assert code == 0
    assert "Verdict: REVIEW" in output
    assert "WARN visual.dual_axis.review:" in output
    assert "ad_spend" in output and "sales" in output
    assert main(args + ["--warnings-as-errors"]) == 1
