"""Cross-chart total reconciliation: identity, semantics, and hardening."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from chart_contract import audit_bundle
from chart_contract.bundle import parse_bundle_manifest
from chart_contract.cli import main

TRAPS = Path(__file__).resolve().parents[1] / "examples" / "traps"
BUNDLE = TRAPS / "cross_chart_total_gap.bundle.json"
SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "audit-bundle-v1.schema.json"


def _fixture():
    manifest = json.loads(BUNDLE.read_text(encoding="utf-8"))
    inputs = {}
    for item in manifest["artifacts"]:
        inputs[item["id"]] = (
            json.loads((TRAPS / item["spec"]).read_text(encoding="utf-8")),
            pd.read_csv(TRAPS / item["data"]),
            item.get("claim"),
        )
    return manifest, inputs


def _finding(report, rule):
    return next(f for f in report.findings if f.rule_id == rule)


def test_hero_individual_charts_ready_but_total_gap_blocks():
    manifest, inputs = _fixture()
    report = audit_bundle(manifest, inputs)
    assert [r.verdict for r in report.artifact_reports.values()] == ["READY", "READY"]
    assert report.verdict == "BLOCK"
    assert _finding(report, "bundle.reconciliation.evidence").severity == "PASS"
    difference = _finding(report, "bundle.reconciliation.total")
    assert difference.severity == "FAIL"
    assert "920" in difference.message
    assert "1000" in difference.message
    assert "residual=80" in difference.message
    assert "represented_share=92.0%" in difference.message
    assert report.to_dict()["relationships"][0]["kind"] == "sum_reconciliation"


def test_corrected_components_pass_when_sum_equals_headline():
    manifest, inputs = _fixture()
    spec, frame, claim = inputs["breakdown"]
    frame = frame.copy()
    frame.loc[frame["channel"] == "Partnerships", "channel_sales"] = 200
    inputs["breakdown"] = (spec, frame, claim)
    report = audit_bundle(manifest, inputs)
    assert report.verdict == "READY"
    assert _finding(report, "bundle.reconciliation.evidence").severity == "PASS"
    assert _finding(report, "bundle.reconciliation.total").severity == "PASS"


def test_explicit_absolute_tolerance_never_uses_implicit_relative_slack():
    manifest, inputs = _fixture()
    relation = manifest["relationships"][0]
    spec, frame, claim = inputs["breakdown"]
    frame = frame.copy()
    frame.loc[frame["channel"] == "Partnerships", "channel_sales"] = 199.5
    inputs["breakdown"] = (spec, frame, claim)
    assert _finding(audit_bundle(manifest, inputs), "bundle.reconciliation.total").severity == "FAIL"
    relation["tolerance"] = 0.5
    assert _finding(audit_bundle(manifest, inputs), "bundle.reconciliation.total").severity == "PASS"


def test_multiple_independent_identity_and_sum_relationships():
    manifest, inputs = _fixture()
    manifest["relationships"].append({
        "id": "shared_unit", "artifact_ids": ["headline", "breakdown"], "equal_on": ["unit"]
    })
    report = audit_bundle(manifest, inputs)
    assert _finding(report, "bundle.identity.unit").severity == "PASS"
    assert _finding(report, "bundle.reconciliation.total").severity == "FAIL"


def test_units_are_required_and_must_match():
    manifest, inputs = _fixture()
    spec, frame, claim = inputs["breakdown"]
    spec = deepcopy(spec)
    spec["usermeta"]["unit"] = "dollars"
    inputs["breakdown"] = (spec, frame, claim)
    assert _finding(audit_bundle(manifest, inputs), "bundle.reconciliation.evidence").severity == "FAIL"
    spec["usermeta"].pop("unit")
    assert _finding(audit_bundle(manifest, inputs), "bundle.reconciliation.evidence").severity == "FAIL"


def test_ratio_like_metric_unit_rejected():
    manifest, inputs = _fixture()
    for key in inputs:
        spec, frame, claim = inputs[key]
        spec = deepcopy(spec)
        spec["usermeta"]["unit"] = "rate"
        inputs[key] = (spec, frame, claim)
    report = audit_bundle(manifest, inputs)
    assert _finding(report, "bundle.reconciliation.evidence").severity == "FAIL"
    assert "does not support percent, rate, or ratio" in _finding(
        report, "bundle.reconciliation.evidence"
    ).message


def test_breakdown_duplicate_component_labels_fail_not_double_count():
    manifest, inputs = _fixture()
    spec, frame, claim = inputs["breakdown"]
    frame = frame.copy()
    frame.loc[1, "channel"] = frame.loc[0, "channel"]
    inputs["breakdown"] = (spec, frame, claim)
    report = audit_bundle(manifest, inputs)
    assert report.verdict == "BLOCK"
    assert _finding(report, "bundle.reconciliation.evidence").severity == "FAIL"


@pytest.mark.parametrize("bad", [None, "", True, float("inf"), float("nan"), "100"])
def test_invalid_headline_total_is_refused(bad):
    manifest, inputs = _fixture()
    spec, frame, claim = inputs["headline"]
    frame = frame.copy()
    frame["sales_total"] = pd.Series([bad], dtype=object)
    inputs["headline"] = (spec, frame, claim)
    report = audit_bundle(manifest, inputs)
    assert report.verdict == "BLOCK"
    assert any(
        f.rule_id == "bundle.reconciliation.evidence" and f.severity == "FAIL"
        for f in report.findings
    ) or any(f.rule_id == "bundle.reconciliation.skipped" for f in report.findings)


def test_headline_must_be_one_row_not_an_unacknowledged_series():
    manifest, inputs = _fixture()
    spec, frame, claim = inputs["headline"]
    inputs["headline"] = (spec, pd.concat([frame, frame], ignore_index=True), claim)
    assert _finding(audit_bundle(manifest, inputs), "bundle.reconciliation.evidence").severity == "FAIL"


def test_missing_source_evidence_fails_closed():
    manifest, inputs = _fixture()
    spec, frame, claim = inputs["breakdown"]
    inputs["breakdown"] = (spec, None, claim)
    assert _finding(audit_bundle(manifest, inputs), "bundle.reconciliation.evidence").severity == "FAIL"


def test_source_is_not_mutated_or_rewritten_to_make_sum_pass():
    manifest, inputs = _fixture()
    before = {k: (deepcopy(v[0]), v[1].copy(deep=True)) for k, v in inputs.items()}
    audit_bundle(manifest, inputs)
    for key, (spec, frame) in before.items():
        assert inputs[key][0] == spec
        pd.testing.assert_frame_equal(inputs[key][1], frame)


@pytest.mark.parametrize("edit", [
    lambda s: s.update(transform=[{"filter": "datum.channel_sales > 100"}]),
    lambda s: s["encoding"]["y"].update(aggregate="sum"),
    lambda s: s["encoding"]["x"].update(bin=True),
    lambda s: s["encoding"].update(color={"field": "channel", "type": "nominal"}),
    lambda s: s.update(layer=[{"mark": "bar"}]),
])
def test_transformed_or_unsupported_breakdown_is_not_mistaken_for_raw_evidence(edit):
    manifest, inputs = _fixture()
    spec, frame, claim = inputs["breakdown"]
    spec = deepcopy(spec)
    edit(spec)
    inputs["breakdown"] = (spec, frame, claim)
    report = audit_bundle(manifest, inputs)
    assert report.verdict == "BLOCK"
    findings = {f.rule_id: f.severity for f in report.findings}
    assert (
        findings.get("bundle.reconciliation.evidence") == "FAIL"
        or findings.get("bundle.reconciliation.skipped") == "WARN"
    )


def test_blocked_component_skips_comparison_instead_of_fabricating_pass():
    manifest, inputs = _fixture()
    spec, frame, claim = inputs["breakdown"]
    spec = deepcopy(spec)
    spec["encoding"]["y"]["field"] = "nonexistent_field"
    inputs["breakdown"] = (spec, frame, claim)
    report = audit_bundle(manifest, inputs)
    assert report.artifact_reports["breakdown"].verdict == "BLOCK"
    assert report.verdict == "BLOCK"
    assert _finding(report, "bundle.reconciliation.skipped").severity == "WARN"
    assert all(f.rule_id != "bundle.reconciliation.total" for f in report.findings)


def test_review_component_propagates_while_valid_sum_relation_still_passes():
    manifest, inputs = _fixture()
    spec, frame, claim = inputs["headline"]
    spec = deepcopy(spec)
    spec["usermeta"].pop("source")
    inputs["headline"] = (spec, frame, claim)
    bspec, bframe, bclaim = inputs["breakdown"]
    bframe = bframe.copy()
    bframe.loc[bframe["channel"] == "Partnerships", "channel_sales"] = 200
    inputs["breakdown"] = (bspec, bframe, bclaim)
    report = audit_bundle(manifest, inputs)
    assert report.artifact_reports["headline"].verdict == "REVIEW"
    assert report.verdict == "REVIEW"
    assert _finding(report, "bundle.reconciliation.total").severity == "PASS"


@pytest.mark.parametrize("mutation", [
    lambda r: r.update(kind="identity"),
    lambda r: r.update(extra="unrecognized"),
    lambda r: r.pop("components_exhaustive"),
    lambda r: r.update(components_exhaustive=False),
    lambda r: r.update(components_exhaustive=1),
    lambda r: r.update(tolerance=-1),
    lambda r: r.update(tolerance=True),
    lambda r: r.update(tolerance=float("inf")),
    lambda r: r.update(tolerance=float("nan")),
    lambda r: r.update(total_artifact_id="unknown"),
    lambda r: r.update(components_artifact_id="headline"),
    lambda r: r.update(component_field="channel_sales"),
    lambda r: r.update(total_metric_field=""),
])
def test_malformed_typed_relationship_is_fail_closed(mutation):
    manifest, _ = _fixture()
    mutation(manifest["relationships"][0])
    with pytest.raises(ValueError):
        parse_bundle_manifest(manifest)


def test_duplicate_relationship_ids_fail_across_kinds():
    manifest, _ = _fixture()
    manifest["relationships"].append({
        "id": "sales_breakdown_matches_headline",
        "artifact_ids": ["headline", "breakdown"], "equal_on": ["unit"],
    })
    with pytest.raises(ValueError, match="unique"):
        parse_bundle_manifest(manifest)


def test_schema_accepts_legacy_and_typed_shape_as_distinct_variants():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    kinds = schema["properties"]["relationships"]["items"]["oneOf"]
    assert len(kinds) == 2
    assert kinds[0]["required"] == ["id", "artifact_ids", "equal_on"]
    assert kinds[1]["properties"]["kind"]["const"] == "sum_reconciliation"
    assert kinds[1]["properties"]["components_exhaustive"]["const"] is True
    assert kinds[1]["additionalProperties"] is False


def test_cli_hero_reports_individually_ready_and_bundle_block(capsys):
    assert main(["audit", "bundle", str(BUNDLE)]) == 1
    output = capsys.readouterr().out
    assert "Verdict: BLOCK" in output
    assert "headline: READY" in output
    assert "breakdown: READY" in output
    assert "PASS bundle.reconciliation.evidence" in output
    assert "FAIL bundle.reconciliation.total" in output
    assert "residual=80" in output


def test_cli_json_and_markdown_contain_cross_total_finding(capsys):
    assert main(["audit", "bundle", str(BUNDLE), "--format", "json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "BLOCK"
    assert payload["relationships"][0]["kind"] == "sum_reconciliation"
    assert any(x["rule_id"] == "bundle.reconciliation.total" for x in payload["findings"])
    assert all(x["report"]["input_binding"] for x in payload["artifacts"])
    assert main(["audit", "bundle", str(BUNDLE), "--format", "markdown"]) == 1
    markdown = capsys.readouterr().out
    assert "bundle.reconciliation.total" in markdown


def test_deterministic_report_and_manifest_hash_for_identical_inputs():
    manifest, inputs = _fixture()
    first = audit_bundle(manifest, inputs).to_dict()
    second = audit_bundle(manifest, inputs).to_dict()
    assert first == second
