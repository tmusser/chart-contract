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
BUNDLE_FILE = TRAPS / "cross_chart_scope_mismatch.bundle.json"


def _fixture_inputs():
    manifest = json.loads(BUNDLE_FILE.read_text(encoding="utf-8"))
    inputs = {}
    for item in manifest["artifacts"]:
        inputs[item["id"]] = (
            json.loads((TRAPS / item["spec"]).read_text(encoding="utf-8")),
            pd.read_csv(TRAPS / item["data"]),
            item.get("claim"),
        )
    return manifest, inputs


def _scope(spec, identity):
    spec["usermeta"]["analysis_scope_contract"]["scope_id"] = identity
    spec["usermeta"]["analysis_scope_contract"]["scope_definition"] = identity
    spec["usermeta"]["analysis_scope_contract"]["scope_basis_value"] = identity


def _finding(report, rule_id):
    return next(f for f in report.findings if f.rule_id == rule_id)


def test_hero_two_ready_artifacts_still_block_on_cross_scope():
    manifest, inputs = _fixture_inputs()
    report = audit_bundle(manifest, inputs)
    assert [r.verdict for r in report.artifact_reports.values()] == ["READY", "READY"]
    assert report.verdict == "BLOCK"
    finding = _finding(report, "bundle.identity.analysis_scope")
    assert finding.severity == "FAIL"
    assert "us_paid_customers" in finding.message
    assert "all_customers" in finding.message
    payload = report.to_dict()
    assert payload["type"] == "chart_contract.audit_bundle_report"
    assert len(payload["manifest_sha256"]) == 64
    assert all(item["report"]["input_binding"]["bundle_sha256"] for item in payload["artifacts"])


def test_same_scope_passes_even_when_metric_fields_differ():
    manifest, inputs = _fixture_inputs()
    spec, df, claim = inputs["churn"]
    spec = deepcopy(spec)
    df = df.copy()
    _scope(spec, "us_paid_customers")
    spec["usermeta"]["analysis_scope_contract"]["scope_definition"] = "US paid customers."
    df["scope_basis"] = "us_paid_v1"
    spec["usermeta"]["analysis_scope_contract"]["scope_basis_value"] = "us_paid_v1"
    inputs["churn"] = (spec, df, claim)
    report = audit_bundle(manifest, inputs)
    assert report.verdict == "READY"
    assert _finding(report, "bundle.identity.analysis_scope").severity == "PASS"


def test_missing_declaration_is_block_when_same_scope_explicitly_required():
    manifest, inputs = _fixture_inputs()
    spec, df, claim = inputs["churn"]
    spec = deepcopy(spec)
    del spec["usermeta"]["analysis_scope_contract"]
    inputs["churn"] = (spec, df, claim)
    report = audit_bundle(manifest, inputs)
    assert report.verdict == "BLOCK"
    assert _finding(report, "bundle.identity.analysis_scope").severity == "FAIL"


def test_broken_component_propagates_block_without_false_identity_pass():
    manifest, inputs = _fixture_inputs()
    spec, df, claim = inputs["growth"]
    spec = deepcopy(spec)
    spec["encoding"]["y"]["field"] = "nonexistent_metric"
    inputs["growth"] = (spec, df, claim)
    report = audit_bundle(manifest, inputs)
    assert report.artifact_reports["growth"].verdict == "BLOCK"
    assert report.verdict == "BLOCK"
    assert _finding(report, "bundle.identity.skipped").severity == "WARN"


def test_component_review_propagates_without_changing_relation_result():
    manifest, inputs = _fixture_inputs()
    spec, df, claim = inputs["growth"]
    spec = deepcopy(spec)
    del spec["usermeta"]["source"]
    inputs["growth"] = (spec, df, claim)
    spec2, df2, claim2 = inputs["churn"]
    spec2 = deepcopy(spec2)
    df2 = df2.copy()
    spec2["usermeta"]["analysis_scope_contract"] = deepcopy(spec["usermeta"]["analysis_scope_contract"])
    df2["scope_basis"] = "us_paid_v1"
    inputs["churn"] = (spec2, df2, claim2)
    report = audit_bundle(manifest, inputs)
    assert report.verdict == "REVIEW"
    assert _finding(report, "bundle.identity.analysis_scope").severity == "PASS"


def test_opt_in_metric_identity_equality_ignores_local_y_column_name():
    manifest, inputs = _fixture_inputs()
    manifest["relationships"][0]["equal_on"] = ["metric_definition"]
    for identifier in inputs:
        spec, data, claim = inputs[identifier]
        spec = deepcopy(spec)
        metric_field = spec["encoding"]["y"]["field"]
        spec["usermeta"]["metric_definition_contract"] = {
            "version": 1, "metric_field": metric_field,
            "metric_id": "active_users", "metric_definition": "Active users in the declared cohort.",
            "metric_version": "v1", "metric_basis_field": None,
        }
        inputs[identifier] = (spec, data, claim)
    report = audit_bundle(manifest, inputs)
    assert _finding(report, "bundle.identity.metric_definition").severity == "PASS"
    assert report.verdict == "READY"
    spec, data, claim = inputs["churn"]
    bad = deepcopy(spec)
    bad["usermeta"]["metric_definition_contract"]["metric_version"] = "v2"
    inputs["churn"] = (bad, data, claim)
    assert _finding(audit_bundle(manifest, inputs), "bundle.identity.metric_definition").severity == "FAIL"


def test_opt_in_unit_and_scale_parity():
    manifest, inputs = _fixture_inputs()
    manifest["relationships"][0]["equal_on"] = ["unit"]
    assert audit_bundle(manifest, inputs).verdict == "READY"
    spec, data, claim = inputs["churn"]
    spec = deepcopy(spec)
    spec["usermeta"]["unit"] = "sessions"
    inputs["churn"] = (spec, data, claim)
    assert _finding(audit_bundle(manifest, inputs), "bundle.identity.unit").severity == "FAIL"


def test_opt_in_window_parity_requires_exact_windows():
    manifest, inputs = _fixture_inputs()
    manifest["relationships"][0]["equal_on"] = ["time_window"]
    base_window = {
        "version": 1, "window_kind": "rolling", "window_granularity": None,
        "baseline_start": "2026-01-01", "baseline_end": "2026-01-07",
        "target_start": "2026-01-08", "target_end": "2026-01-14",
        "baseline_complete": True, "target_complete": True,
        "baseline_days": 7, "target_days": 7,
    }
    for identifier in inputs:
        spec, data, claim = inputs[identifier]
        spec = deepcopy(spec)
        spec["usermeta"]["time_window_contract"] = deepcopy(base_window)
        inputs[identifier] = (spec, data, claim)
    report = audit_bundle(manifest, inputs)
    assert _finding(report, "bundle.identity.time_window").severity == "PASS"
    spec, data, claim = inputs["churn"]
    spec = deepcopy(spec)
    spec["usermeta"]["time_window_contract"]["target_end"] = "2026-01-15"
    spec["usermeta"]["time_window_contract"]["target_days"] = 8
    inputs["churn"] = (spec, data, claim)
    assert _finding(audit_bundle(manifest, inputs), "bundle.identity.time_window").severity == "FAIL"


@pytest.mark.parametrize("mutation", [
    lambda m: m.update(version=True),
    lambda m: m.update(extra=123),
    lambda m: m.update(relationships=[]),
    lambda m: m["relationships"][0].update(artifact_ids=["growth", "growth"]),
    lambda m: m["relationships"][0].update(artifact_ids=["growth", "unknown"]),
    lambda m: m["relationships"][0].update(equal_on=["scope"]),
    lambda m: m["relationships"][0].update(equal_on=[]),
    lambda m: m["artifacts"].append(deepcopy(m["artifacts"][0])),
    lambda m: m["relationships"][0].update(extra="oops"),
])
def test_malformed_manifest_fails_closed(mutation):
    manifest, _ = _fixture_inputs()
    mutation(manifest)
    with pytest.raises(ValueError):
        parse_bundle_manifest(manifest)


def test_exact_input_set_required():
    manifest, inputs = _fixture_inputs()
    del inputs["churn"]
    with pytest.raises(ValueError, match="exactly"):
        audit_bundle(manifest, inputs)


def test_cli_cross_chart_trap_exits_block(capsys):
    code = main(["audit", "bundle", str(BUNDLE_FILE)])
    output = capsys.readouterr().out
    assert code == 1
    assert "Verdict: BLOCK" in output
    assert "growth: READY" in output
    assert "churn: READY" in output
    assert "FAIL bundle.identity.analysis_scope" in output


def test_cli_json_report_includes_component_input_and_policy_bindings(capsys):
    code = main(["audit", "bundle", str(BUNDLE_FILE), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["verdict"] == "BLOCK"
    assert all(item["report"]["report_binding"] for item in payload["artifacts"])


def test_cli_output_and_markdown_paths(tmp_path, capsys):
    json_path, markdown_path = tmp_path / "output.json", tmp_path / "output.md"
    code = main([
        "audit", "bundle", str(BUNDLE_FILE), "--format", "json",
        "--out", str(json_path), "--markdown", str(markdown_path),
    ])
    assert code == 1
    assert "Verdict: BLOCK" in capsys.readouterr().out
    assert json.loads(json_path.read_text())["verdict"] == "BLOCK"
    assert markdown_path.read_text().startswith("# Audit Bundle Report")


def test_cli_rejects_path_escape(tmp_path, capsys):
    manifest, _ = _fixture_inputs()
    manifest["artifacts"][0]["spec"] = "../outside.vl.json"
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main(["audit", "bundle", str(path)])
    assert exc.value.code == 2
    assert "within the manifest directory" in capsys.readouterr().err


def test_bundle_report_is_deterministic_across_repeated_audits():
    manifest, inputs = _fixture_inputs()
    first = audit_bundle(manifest, inputs).to_dict()
    second = audit_bundle(manifest, inputs).to_dict()
    assert first == second
