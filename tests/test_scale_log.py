"""Log-axis source visibility: distinguish valid negative-only domains from contradictions."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from chart_contract import audit_spec
from chart_contract.cli import main


TRAPS = Path(__file__).resolve().parents[1] / "examples" / "traps"
RULE = "visual.scale.log_domain"


def _data(values=(2.0, 4.0, 8.0, 16.0)):
    return pd.DataFrame({
        "week": ["W1", "W2", "W3", "W4"],
        "net_return": list(values),
    })


def _spec(scale=None, *, mark="line"):
    encoding = {
        "x": {"field": "week", "type": "ordinal"},
        "y": {"field": "net_return", "type": "quantitative"},
    }
    if scale is not None:
        encoding["y"]["scale"] = scale
    return {
        "mark": mark, "title": "Recorded weekly net returns",
        "encoding": encoding,
        "usermeta": {
            "source": "synthetic.log_domain",
            "unit": "USD",
            "claim": "Recorded net returns vary across four weeks.",
            "user_requested_scale_override": True,
        },
    }


def _findings(report):
    return [finding for finding in report.findings if finding.rule_id == RULE]


def _one(spec, data=None):
    findings = _findings(audit_spec(spec, data=_data() if data is None else data))
    assert len(findings) == 1
    return findings[0]


@pytest.mark.parametrize("values,scale", [
    ([1.0, 3.0, 10.0, 100.0], {"type": "log"}),
    ([1.0, 3.0, 10.0, 100.0], {"type": "log", "domain": [1, 100]}),
    ([-100.0, -30.0, -4.0, -1.0], {"type": "log"}),
    ([-100.0, -30.0, -4.0, -1.0], {"type": "log", "domain": [-100, -1]}),
    ([1.0, 3.0, 10.0, 100.0], {"type": "log", "domainMin": 1}),
    ([-100.0, -30.0, -4.0, -1.0], {"type": "log", "domainMax": -1}),
])
def test_same_sign_log_evidence_passes(values, scale):
    finding = _one(_spec(scale), _data(values))
    assert finding.severity == "PASS"
    assert ("strictly positive" in finding.message or "strictly negative" in finding.message)


@pytest.mark.parametrize("values,expected", [
    ([2.0, 0.0, 5.0, 8.0], "1 of 4"),
    ([-1.0, 0.0, -5.0, -8.0], "1 of 4"),
    ([0.0, 0.0, 3.0, 4.0], "2 of 4"),
    ([2.0, 5.0, -1.0, 8.0], "3 positive and 1 negative"),
    ([-2.0, -5.0, 1.0, -8.0], "1 positive and 3 negative"),
])
def test_unrepresentable_zero_or_mixed_sign_blocks(values, expected):
    spec = _spec({"type": "log"})
    report = audit_spec(spec, data=_data(values))
    assert report.verdict == "BLOCK"
    finding = _findings(report)[0]
    assert finding.severity == "FAIL"
    assert expected in finding.message


@pytest.mark.parametrize("scale,values", [
    ({"type": "log", "domain": [1, 100]}, [-100.0, -25.0, -10.0, -2.0]),
    ({"type": "log", "domain": [-100, -1]}, [2.0, 10.0, 30.0, 99.0]),
    ({"type": "log", "domainMin": 1}, [-1.0, -2.0, -3.0, -4.0]),
    ({"type": "log", "domainMax": -1}, [2.0, 3.0, 4.0, 5.0]),
])
def test_incompatible_explicit_domain_fails(values, scale):
    item = _one(_spec(scale), _data(values))
    assert item.severity == "FAIL"
    assert "only" in item.message


@pytest.mark.parametrize("scale,reason", [
    ({"type": "log", "domain": [0, 100]}, "includes zero"),
    ({"type": "log", "domain": [-100, 0]}, "includes zero"),
    ({"type": "log", "domain": [-1, 100]}, "crosses zero"),
    ({"type": "log", "domain": [-1e-300, 1e-300]}, "crosses zero"),
    ({"type": "log", "domainMin": 0}, "includes zero"),
    ({"type": "log", "domainMax": 0}, "includes zero"),
    ({"type": "log", "domainMin": -2, "domainMax": 3}, "crosses zero"),
])
def test_invalid_explicit_domains_fail_even_without_source_rows(scale, reason):
    spec = _spec(scale)
    item = _findings(audit_spec(spec, data=None))[0]
    assert item.severity == "FAIL"
    assert reason in item.message


@pytest.mark.parametrize("scale", [
    {"type": "log", "domainRaw": {"signal": "dynamic"}},
    {"type": "log", "domain": ["x", "y"]},
    {"type": "log", "domain": [2, 2]},
    {"type": "log", "domain": [2, 1]},
    {"type": "log", "domain": [1, 100], "domainMin": 1},
    {"type": "log", "domainMin": -5},
    {"type": "log", "domainMax": 5},
    {"type": "log", "domainMin": True},
])
def test_unknown_or_dynamic_domains_are_review_not_false_pass(scale):
    assert _one(_spec(scale)).severity == "WARN"


def test_dynamic_domain_does_not_hide_proven_zero_contradiction():
    spec = _spec({"type": "log", "domainRaw": {"signal": "dynamic"}})
    assert _one(spec, _data([0, 2, 4, 8])).severity == "FAIL"


def test_no_source_evidence_is_unverifiable_not_pass():
    spec = _spec({"type": "log"})
    findings = _findings(audit_spec(spec, data=None))
    assert len(findings) == 1
    assert findings[0].severity == "WARN"
    assert "source observations are unavailable" in findings[0].message


def test_inline_evidence_gets_a_direct_check():
    spec = _spec({"type": "log"})
    spec["data"] = {"values": _data([1.0, -2.0, 3.0, 4.0]).to_dict("records")}
    finding = _findings(audit_spec(spec, data=None))[0]
    assert finding.severity == "FAIL"
    assert "positive" in finding.message and "negative" in finding.message


def test_incomplete_source_rows_never_produce_pass():
    item = _one(_spec({"type": "log"}), _data([1.0, None, 3.0, 4.0]))
    assert item.severity == "WARN"
    assert "invalid/null" in item.message


def test_missing_encoded_field_cannot_get_pass():
    spec = _spec({"type": "log"})
    spec["encoding"]["y"]["field"] = "missing"
    assert _one(spec).severity == "WARN"


def test_non_numeric_metric_does_not_claim_coverage():
    spec = _spec({"type": "log"})
    item = _one(spec, _data([1, "bad", 3, 4]))
    assert item.severity == "WARN"


def test_all_non_numeric_metric_warns_not_passes():
    spec = _spec({"type": "log"})
    item = _one(spec, _data(["bad", "bad", "bad", "bad"]))
    assert item.severity == "WARN"


def test_x_and_y_log_axes_both_emit_distinct_findings():
    spec = _spec({"type": "log"})
    spec["mark"] = "point"
    spec["encoding"]["x"] = {
        "field": "score", "type": "quantitative", "scale": {"type": "log"}
    }
    data = _data([3.0, 5.0, 6.0, 7.0]).assign(score=[1.0, 0.0, 2.0, 4.0])
    report = audit_spec(spec, data=data)
    findings = _findings(report)
    assert len(findings) == 2
    assert {f.field for f in findings} == {"encoding.x.scale", "encoding.y.scale"}
    assert next(f.severity for f in findings if f.field == "encoding.x.scale") == "FAIL"
    assert next(f.severity for f in findings if f.field == "encoding.y.scale") == "PASS"


def test_transformed_spec_is_unverifiable_not_claimed_checked():
    spec = _spec({"type": "log"})
    spec["transform"] = [{"filter": "datum.net_return > 0"}]
    assert _one(spec, _data([0, 1, 2, 3])).severity == "WARN"


def test_encoding_aggregate_is_not_mistaken_for_raw_log_values():
    spec = _spec({"type": "log"})
    spec["encoding"]["y"]["aggregate"] = "sum"
    assert _one(spec).severity == "WARN"


def test_layered_view_receives_unverifiable_warning():
    spec = _spec({"type": "log"})
    child = {"mark": "line", "encoding": spec["encoding"]}
    del spec["encoding"]
    del spec["mark"]
    spec["layer"] = [child]
    findings = _findings(audit_spec(spec, data=_data()))
    assert len(findings) == 1
    assert findings[0].severity == "WARN"


def test_unsupported_area_mark_cannot_get_a_pass():
    spec = _spec({"type": "log"}, mark="area")
    assert _one(spec).severity == "WARN"


@pytest.mark.parametrize("scale", [
    {"type": "symlog"},
    {"type": "linear"},
    {"type": "sqrt"},
    {"type": "logarithmic"},
])
def test_other_scale_types_do_not_emit_log_rule(scale):
    assert not _findings(audit_spec(_spec(scale), data=_data([0, -2, 2, 8])))


def test_log_scale_on_categorical_axis_is_out_of_scope():
    spec = _spec()
    spec["encoding"]["x"]["scale"] = {"type": "log"}
    assert not _findings(audit_spec(spec, data=_data()))


def test_implicit_scale_has_no_new_finding():
    assert not _findings(audit_spec(_spec(), data=_data()))


def test_source_and_spec_are_not_mutated():
    spec = _spec({"type": "log"})
    frame = _data([2.0, 0.0, -5.0, 8.0])
    saved_spec, saved_frame = deepcopy(spec), frame.copy(deep=True)
    audit_spec(spec, data=frame)
    assert spec == saved_spec
    pd.testing.assert_frame_equal(frame, saved_frame)


def test_cli_log_visibility_trap_blocks_with_authorization_pass(capsys):
    args = [
        "audit", "spec", str(TRAPS / "mixed_sign_log_axis.vl.json"),
        "--data", str(TRAPS / "mixed_sign_log_axis.csv"),
        "--claim", (TRAPS / "mixed_sign_log_axis.claim.txt").read_text().strip(),
    ]
    code = main(args)
    output = capsys.readouterr().out
    assert code == 1
    assert "Verdict: BLOCK" in output
    assert "FAIL visual.scale.log_domain:" in output
    assert "3 positive and 1 negative" in output
    assert "PASS scale.override.authorization" in output
