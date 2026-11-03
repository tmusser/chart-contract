"""Axis clipping audits: explicit scale bounds versus plotted source observations."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from chart_contract import audit_spec
from chart_contract.cli import main

TRAPS = Path(__file__).resolve().parents[1] / "examples" / "traps"
RULE = "visual.scale.clipped_data"


def _spec(*, domain=None, requested=True, clip=True):
    spec = {
        "mark": {"type": "line", "clip": clip},
        "title": "Recorded weekly returns",
        "encoding": {
            "x": {"field": "week", "type": "ordinal"},
            "y": {"field": "returns", "type": "quantitative"},
        },
        "usermeta": {
            "source": "synthetic.axis_limits",
            "unit": "dollars",
            "claim": "Recorded returns vary across the four displayed weeks.",
        },
    }
    if requested:
        spec["usermeta"]["user_requested_scale_override"] = True
    if domain is not None:
        spec["encoding"]["y"]["scale"] = domain
    return spec


def _data():
    return pd.DataFrame({
        "week": ["W1", "W2", "W3", "W4"],
        "returns": [5.0, 8.0, -80.0, 11.0],
    })


def _findings(report):
    return [x for x in report.findings if x.rule_id == RULE]


def test_authorized_zoom_still_warns_on_hidden_extreme():
    spec = _spec(domain={"domain": [0, 15]})
    report = audit_spec(spec, data=_data())
    assert report.verdict == "REVIEW"
    assert next(x.severity for x in report.findings
                if x.rule_id == "scale.override.authorization") == "PASS"
    match = _findings(report)
    assert len(match) == 1
    assert match[0].severity == "WARN"
    assert "1 of 4" in match[0].message
    assert "-80" in match[0].message
    assert "Mark clipping is enabled" in match[0].message


def test_without_authorization_existing_block_remains():
    report = audit_spec(_spec(domain={"domain": [0, 15]}, requested=False), data=_data())
    assert report.verdict == "BLOCK"
    assert _findings(report)[0].severity == "WARN"
    assert next(x.severity for x in report.findings
                if x.rule_id == "scale.override.authorization") == "FAIL"


def test_complete_numeric_range_passes_without_warning():
    report = audit_spec(_spec(domain={"domain": [-80, 15]}), data=_data())
    assert _findings(report)[0].severity == "PASS"
    assert report.verdict == "READY"


def test_exact_domain_endpoints_are_included():
    spec = _spec(domain={"domain": [-80, 11]})
    assert _findings(audit_spec(spec, data=_data()))[0].severity == "PASS"


@pytest.mark.parametrize(("scale", "expected"), [
    ({"domainMin": 0}, "WARN"),
    ({"domainMax": 9}, "WARN"),
    ({"domainMin": -100}, "PASS"),
    ({"domainMax": 100}, "PASS"),
    ({"domainMin": -80, "domainMax": 11}, "PASS"),
])
def test_partial_or_full_numeric_limits(scale, expected):
    report = audit_spec(_spec(domain=scale), data=_data())
    assert _findings(report)[0].severity == expected


def test_quantitative_x_domain_detects_outside_values():
    spec = _spec()
    spec["mark"] = "point"
    spec["encoding"]["x"] = {
        "field": "day", "type": "quantitative",
        "scale": {"domain": [0, 3]},
    }
    data = _data().assign(day=[-2, 1, 2, 3])
    report = audit_spec(spec, data=data)
    item = _findings(report)
    assert len(item) == 1
    assert item[0].severity == "WARN"
    assert "day" in item[0].message
    assert "-2" in item[0].message


def test_x_and_y_outside_produce_separate_findings():
    spec = _spec(domain={"domain": [0, 15]})
    spec["mark"] = "point"
    spec["encoding"]["x"] = {
        "field": "day", "type": "quantitative", "scale": {"domain": [0, 3]},
    }
    data = _data().assign(day=[-2, 1, 2, 3])
    findings = _findings(audit_spec(spec, data=data))
    assert len(findings) == 2
    assert all(x.severity == "WARN" for x in findings)
    assert {x.field for x in findings} == {"encoding.x.scale", "encoding.y.scale"}


def test_not_clipped_mark_still_flags_off_axis_points():
    spec = _spec(domain={"domain": [0, 15]}, clip=False)
    item = _findings(audit_spec(spec, data=_data()))[0]
    assert item.severity == "WARN"
    assert "off-plot or clipped" in item.message


def test_implicit_scale_does_not_emit_clipping_rule():
    report = audit_spec(_spec(), data=_data())
    assert not _findings(report)


def test_zero_false_alone_has_no_explicit_numeric_bounds():
    report = audit_spec(_spec(domain={"zero": False}), data=_data())
    assert not _findings(report)


@pytest.mark.parametrize("bad", [
    {"domainRaw": {"signal": "dynamicRange"}},
    {"domain": {"signal": "dynamicRange"}},
    {"domain": [0, "max"]},
    {"domain": [15, 0]},
    {"domain": [True, 15]},
    {"domain": [0, float("inf")]},
    {"domainMin": 5, "domainMax": 5},
    {"domain": [0, 15], "domainMin": 0},
])
def test_dynamic_or_unsupported_bounds_warn_not_pass(bad):
    assert _findings(audit_spec(_spec(domain=bad), data=_data()))[0].severity == "WARN"


def test_missing_evidence_yields_unverifiable_warning():
    spec = _spec(domain={"domain": [0, 15]})
    report = audit_spec(spec, data=None)
    item = _findings(report)[0]
    assert item.severity == "WARN"
    assert "without reconstructable source rows" in item.message


def test_inline_vegalite_evidence_is_verified():
    spec = _spec(domain={"domain": [0, 15]})
    spec["data"] = {"values": _data().to_dict(orient="records")}
    assert "1 of 4" in _findings(audit_spec(spec, data=None))[0].message


def test_transformed_spec_is_not_misreported_as_verified():
    spec = _spec(domain={"domain": [0, 15]})
    spec["transform"] = [{"filter": "datum.returns > 0"}]
    item = _findings(audit_spec(spec, data=_data()))[0]
    assert item.severity == "WARN"
    assert "Cannot verify" in item.message


def test_encoding_aggregate_is_not_treated_as_raw_axis():
    spec = _spec(domain={"domain": [0, 15]})
    spec["encoding"]["y"]["aggregate"] = "mean"
    item = _findings(audit_spec(spec, data=_data()))[0]
    assert item.severity == "WARN"
    assert "computed" in item.message


def test_layered_views_warn_on_unverifiable_coverage():
    spec = _spec(domain={"domain": [0, 15]})
    line = {"mark": {"type": "line", "clip": True}, "encoding": spec["encoding"]}
    spec.pop("mark")
    spec.pop("encoding")
    spec["layer"] = [line]
    items = _findings(audit_spec(spec, data=_data()))
    assert len(items) == 1 and items[0].severity == "WARN"
    assert "layered" in items[0].message


def test_missing_encoded_field_never_claims_coverage():
    spec = _spec(domain={"domain": [0, 15]})
    spec["encoding"]["y"]["field"] = "not_supplied"
    item = _findings(audit_spec(spec, data=_data()))[0]
    assert item.severity == "WARN"
    assert "missing" in item.message


def test_nan_or_null_pairs_prevent_false_coverage_pass():
    spec = _spec(domain={"domain": [-80, 15]})
    source = _data()
    source.loc[1, "returns"] = float("nan")
    item = _findings(audit_spec(spec, data=source))[0]
    assert item.severity == "WARN"
    assert "invalid/null" in item.message


def test_ordinal_axis_domain_not_treated_as_numeric():
    spec = _spec()
    spec["encoding"]["x"]["scale"] = {"domain": ["W1", "W2"]}
    assert not _findings(audit_spec(spec, data=_data()))


def test_invalid_source_column_does_not_mutate_data_or_scale():
    spec = _spec(domain={"domain": [0, 15]})
    data = _data()
    spec_before = deepcopy(spec)
    data_before = data.copy(deep=True)
    audit_spec(spec, data=data)
    assert spec == spec_before
    pd.testing.assert_frame_equal(data, data_before)


def test_cli_hidden_extreme_reviews_and_warnings_as_errors(capsys):
    args = [
        "audit", "spec", str(TRAPS / "hidden_outlier_axis.vl.json"),
        "--data", str(TRAPS / "hidden_outlier_axis.csv"),
        "--claim", (TRAPS / "hidden_outlier_axis.claim.txt").read_text().strip(),
    ]
    code = main(args)
    output = capsys.readouterr().out
    assert code == 0
    assert "Verdict: REVIEW" in output
    assert "WARN visual.scale.clipped_data" in output
    assert "1 of 4" in output
    assert main(args + ["--warnings-as-errors"]) == 1
