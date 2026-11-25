"""Filter impact receipts: source row counts, threshold gates, and fail-closed evidence."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pandas as pd
import pytest

from chart_contract import audit_spec, build_filter_impact_contract, build_transform_lineage
from chart_contract.cli import main
from chart_contract.filter_impact import FilterImpactUnavailable, parse_filter_impact_contract
from chart_contract.input_binding import bound_report_from_dict

TRAPS = Path(__file__).resolve().parents[1] / "examples" / "traps"
RECEIPTS = "data.filter.receipts"
RETENTION = "data.filter.retention"


def _data():
    return pd.DataFrame({
        "segment": ["Core", "Core", "Trial", "Core", "Trial", "Core", "Trial", "Core"],
        "systems": [110, 120, 80, 150, 70, 90, 60, 160],
    })


def _spec(filters=None):
    return {
        "mark": "point",
        "title": "Recorded systems by customer segment",
        "encoding": {
            "x": {"field": "segment", "type": "nominal"},
            "y": {"field": "systems", "type": "quantitative"},
        },
        "transform": filters if filters is not None else [
            {"filter": {"field": "segment", "equal": "Core"}},
        ],
        "usermeta": {
            "source": "synthetic.filter_impact",
            "unit": "systems",
            "claim": "Recorded systems for the retained customer segment.",
            "transform_contract": {"declared": ["filter"]},
        },
    }


def _prepared(*, data=None, filters=None, minimum=75):
    data = _data() if data is None else data
    spec = _spec(filters)
    spec["usermeta"]["transform_lineage"] = build_transform_lineage(spec)
    spec["usermeta"]["filter_impact_contract"] = build_filter_impact_contract(
        spec, data, minimum_retention_pct=minimum,
    )
    return spec, data


def _finding(report, rule):
    return next(item for item in report.findings if item.rule_id == rule)


def test_retention_trap_reviews_37_point_5_pct_excluded_and_structural_checks_pass():
    spec, data = _prepared()
    contract = spec["usermeta"]["filter_impact_contract"]
    assert contract["version"] == 1
    assert contract["minimum_retention_pct"] == 75
    assert contract["receipts"] == [
        {
            "location": "transform[0].filter",
            "operation_sha256": contract["receipts"][0]["operation_sha256"],
            "input_count": 8,
            "retained_count": 5,
            "excluded_count": 3,
            "retained_pct": 62.5,
        }
    ]
    report = audit_spec(spec, data=data)
    assert _finding(report, RECEIPTS).severity == "PASS"
    assert _finding(report, RETENTION).severity == "WARN"
    assert "62.50%" in _finding(report, RETENTION).message
    assert "3 excluded" in _finding(report, RETENTION).message
    assert report.verdict == "REVIEW"
    assert _finding(report, "transform.declaration").severity == "PASS"
    assert _finding(report, "transform.lineage.receipts").severity == "PASS"
    bound_report_from_dict(report.to_dict())


def test_retention_policy_passes_when_same_data_meets_minimum():
    spec, data = _prepared(minimum=60)
    report = audit_spec(spec, data=data)
    assert _finding(report, RECEIPTS).severity == "PASS"
    assert _finding(report, RETENTION).severity == "PASS"
    # Other independent audit warnings must not be conflated with a
    # retention-policy breach.
    assert report.verdict != "BLOCK"


def test_no_threshold_still_discloses_counts_but_does_not_create_arbitrary_gate():
    spec, data = _prepared(minimum=None)
    report = audit_spec(spec, data=data)
    assert _finding(report, RETENTION).severity == "PASS"
    assert "no minimum retention threshold" in _finding(report, RETENTION).message
    assert "8 input row(s), 5 retained, 3 excluded" in _finding(report, RECEIPTS).message


def test_explicit_equal_all_rows_and_none():
    for match, retained in (("Core", 5), ("Trial", 3), ("Missing", 0)):
        spec, data = _prepared(filters=[{"filter": {"field": "segment", "equal": match}}], minimum=0)
        receipt = spec["usermeta"]["filter_impact_contract"]["receipts"][0]
        assert receipt["retained_count"] == retained
        assert receipt["excluded_count"] == 8 - retained
        assert _finding(audit_spec(spec, data=data), RETENTION).severity == "PASS"


def test_two_filters_have_sequential_denominators_and_final_global_threshold():
    filters = [
        {"filter": {"field": "segment", "equal": "Core"}},
        {"filter": {"field": "systems", "gte": 100}},
    ]
    spec, data = _prepared(filters=filters, minimum=60)
    receipts = spec["usermeta"]["filter_impact_contract"]["receipts"]
    assert [(x["input_count"], x["retained_count"], x["excluded_count"]) for x in receipts] == [
        (8, 5, 3), (5, 4, 1)
    ]
    assert receipts[1]["retained_pct"] == 80
    report = audit_spec(spec, data=data)
    assert _finding(report, RECEIPTS).severity == "PASS"
    assert "4 of 8" in _finding(report, RETENTION).message
    assert _finding(report, RETENTION).severity == "WARN"


def test_oneof_string_predicate_is_supported_and_order_is_unchanged():
    filters = [{"filter": {"field": "segment", "oneOf": ["Core", "Trial"]}}]
    spec, data = _prepared(filters=filters, minimum=100)
    assert spec["usermeta"]["filter_impact_contract"]["receipts"][0]["retained_count"] == 8
    assert _finding(audit_spec(spec, data=data), RETENTION).severity == "PASS"


def test_numeric_gt_gte_lt_lte_predicates_recompute_correctly():
    counts = {"gt": 3, "gte": 4, "lt": 4, "lte": 5}
    for op, expected in counts.items():
        spec, data = _prepared(
            filters=[{"filter": {"field": "systems", op: 110}}],
            minimum=None,
        )
        assert spec["usermeta"]["filter_impact_contract"]["receipts"][0]["retained_count"] == expected
        assert _finding(audit_spec(spec, data=data), RECEIPTS).severity == "PASS"


def test_boolean_equal_and_oneof_are_strict_not_int_like():
    data = _data().assign(active=[True, False, True, True, False, True, True, False])
    for predicate in (
        {"field": "active", "equal": True},
        {"field": "active", "oneOf": [True]},
    ):
        spec, _ = _prepared(data=data, filters=[{"filter": predicate}], minimum=None)
        assert spec["usermeta"]["filter_impact_contract"]["receipts"][0]["retained_count"] == 5


def test_source_rebinding_and_stale_counts_fail_even_when_transform_hash_is_unchanged():
    spec, data = _prepared()
    changed = data.copy()
    changed.loc[0, "segment"] = "Trial"
    report = audit_spec(spec, data=changed)
    assert _finding(report, RECEIPTS).severity == "FAIL"
    assert report.verdict == "BLOCK"


def test_changed_filter_operation_fails_independent_receipts_even_if_lineage_is_stale():
    spec, data = _prepared()
    spec["transform"][0]["filter"]["equal"] = "Trial"
    report = audit_spec(spec, data=data)
    assert _finding(report, RECEIPTS).severity == "FAIL"
    assert _finding(report, "transform.lineage.receipts").severity == "FAIL"


@pytest.mark.parametrize("mutate", [
    lambda r: r.update({"retained_count": 4, "excluded_count": 4, "retained_pct": 50}),
    lambda r: r.update({"operation_sha256": "0" * 64}),
    lambda r: r.update({"retained_pct": 50}),
    lambda r: r.update({"location": "transform[99].filter"}),
])
def test_forged_or_stale_receipts_block(mutate):
    spec, data = _prepared()
    mutate(spec["usermeta"]["filter_impact_contract"]["receipts"][0])
    assert _finding(audit_spec(spec, data=data), RECEIPTS).severity == "FAIL"


def test_reordered_rows_with_same_filter_membership_reproduce_counts():
    spec, data = _prepared()
    reordered = data.iloc[::-1].reset_index(drop=True)
    assert _finding(audit_spec(spec, data=reordered), RECEIPTS).severity == "PASS"


def test_missing_or_null_or_wrong_typed_predicate_source_warns_instead_of_passing():
    spec, data = _prepared()
    cases = (
        data.assign(segment=["Core"] * 7 + [None]),
        data.drop(columns=["segment"]),
        data.assign(segment=["Core"] * 7 + [101]),
    )
    for changed in cases:
        report = audit_spec(spec, data=changed)
        assert _finding(report, RECEIPTS).severity == "WARN"
        assert _finding(report, RETENTION).severity == "WARN"


def test_missing_source_evidence_warns_without_claiming_audit_coverage():
    spec, _ = _prepared()
    report = audit_spec(spec, data=None)
    assert _finding(report, RECEIPTS).severity == "WARN"
    assert _finding(report, RETENTION).severity == "WARN"


@pytest.mark.parametrize("filters", [
    [{"filter": "datum.segment === 'Core'"}],
    [{"filter": {"and": [{"field": "segment", "equal": "Core"}]}}],
    [{"filter": {"field": "segment", "equal": "Core", "oneOf": ["Trial"]}}],
    [{"filter": {"field": "systems", "gt": "100"}}],
    [{"filter": {"field": "segment", "equal": None}}],
    [{"filter": {"field": "segment", "oneOf": ["Core", None]}}],
    [{"filter": {"field": "segment", "oneOf": []}}],
    [{"calculate": "datum.systems * 2", "as": "total"}, {"filter": {"field": "segment", "equal": "Core"}}],
    [{"filter": {"field": "segment", "equal": "Core"}}, {"aggregate": [{"op": "count", "as": "n"}]}],
])
def test_unsupported_filter_language_is_never_executed(filters):
    data = _data()
    spec = _spec(filters)
    with pytest.raises(FilterImpactUnavailable):
        build_filter_impact_contract(spec, data)


def test_unsupported_expression_with_claimed_receipts_is_unverifiable_not_false_pass():
    spec, data = _prepared()
    spec["transform"] = [{"filter": "datum.segment === 'Core'"}]
    spec["usermeta"]["transform_lineage"] = build_transform_lineage(spec)
    report = audit_spec(spec, data=data)
    assert _finding(report, RECEIPTS).severity == "WARN"
    assert _finding(report, RETENTION).severity == "WARN"
    assert report.verdict == "REVIEW"


def test_nested_layer_or_concat_is_not_misinterpreted_as_one_input_universe():
    spec, data = _prepared()
    for name in ("layer", "hconcat", "facet"):
        modified = deepcopy(spec)
        modified[name] = []
        report = audit_spec(modified, data=data)
        assert _finding(report, RECEIPTS).severity == "WARN"


@pytest.mark.parametrize("bad_minimum", [-1, 101, True, "75", float("nan")])
def test_invalid_minimum_is_rejected_in_helper(bad_minimum):
    spec = _spec()
    with pytest.raises(ValueError):
        build_filter_impact_contract(spec, _data(), minimum_retention_pct=bad_minimum)


@pytest.mark.parametrize("mutate", [
    lambda c: c.update({"version": True}),
    lambda c: c.update({"version": 2}),
    lambda c: c.update({"minimum_retention_pct": 101}),
    lambda c: c.update({"minimum_retention_pct": "50"}),
    lambda c: c.update({"extra": "bad"}),
    lambda c: c["receipts"][0].update({"bogus": 1}),
    lambda c: c["receipts"][0].update({"input_count": -1}),
    lambda c: c["receipts"][0].update({"retained_pct": float("inf")}),
    lambda c: c.update({"receipts": []}),
])
def test_malformed_closed_contract_blocks(mutate):
    spec, data = _prepared()
    mutate(spec["usermeta"]["filter_impact_contract"])
    assert _finding(audit_spec(spec, data=data), RECEIPTS).severity == "FAIL"


def test_no_optin_contract_preserves_old_transform_only_behavior():
    spec = _spec()
    spec["usermeta"]["transform_lineage"] = build_transform_lineage(spec)
    report = audit_spec(spec, data=_data())
    assert not any(f.rule_id in (RECEIPTS, RETENTION) for f in report.findings)


def test_metadata_not_injected_or_source_changed_by_audit_or_builder():
    spec, data = _prepared()
    spec_before, data_before = deepcopy(spec), data.copy(deep=True)
    assert parse_filter_impact_contract(spec) is not None
    audit_spec(spec, data=data)
    assert spec == spec_before
    pd.testing.assert_frame_equal(data, data_before)


def test_inline_source_rows_recomputed_without_explicit_data_arg():
    spec, data = _prepared()
    spec["data"] = {"values": data.to_dict("records")}
    report = audit_spec(spec, data=None)
    assert _finding(report, RECEIPTS).severity == "PASS"


def test_cap_is_defensive_for_excessive_filter_steps():
    filters = [{"filter": {"field": "segment", "equal": "Core"}}] * 21
    with pytest.raises(FilterImpactUnavailable):
        build_filter_impact_contract(_spec(filters), _data())


def test_retain_zero_rows_does_not_divide_by_zero_across_filter_stages():
    filters = [
        {"filter": {"field": "segment", "equal": "NotHere"}},
        {"filter": {"field": "systems", "gt": 10}},
    ]
    spec, data = _prepared(filters=filters, minimum=50)
    receipts = spec["usermeta"]["filter_impact_contract"]["receipts"]
    assert receipts[0]["input_count"] == 8
    assert receipts[1]["input_count"] == 0
    assert receipts[1]["retained_pct"] == 0
    assert _finding(audit_spec(spec, data=data), RETENTION).severity == "WARN"


def test_cli_filter_impact_trap_warns_when_37_point_5_pct_removed(capsys):
    args = [
        "audit", "spec", str(TRAPS / "high_filter_exclusion.vl.json"),
        "--data", str(TRAPS / "high_filter_exclusion.csv"),
        "--claim", (TRAPS / "high_filter_exclusion.claim.txt").read_text().strip(),
    ]
    assert main(args) == 0
    output = capsys.readouterr().out
    assert "Verdict: REVIEW" in output
    assert "PASS data.filter.receipts:" in output
    assert "WARN data.filter.retention:" in output
    assert "5 of 8" in output
    assert "62.50%" in output
    assert main(args + ["--warnings-as-errors"]) == 1
