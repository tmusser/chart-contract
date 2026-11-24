"""Diff saved bound audit reports without confusing source and policy changes."""

from __future__ import annotations

from copy import deepcopy
import json

import pandas as pd
import pytest

from chart_contract import Chart, audit_spec
from chart_contract.audit import AuditFinding
from chart_contract.cli import main
from chart_contract.input_binding import (
    bound_report_from_dict, build_report_binding, build_input_binding,
)
from chart_contract.profiles import build_audit_profile_binding, get_profile_manifest
from chart_contract.report_diff import build_audit_report_diff, format_audit_diff_text


def _spec():
    return {
        "mark": "line",
        "title": "Recorded weekly sales trend",
        "encoding": {
            "x": {"field": "week", "type": "ordinal"},
            "y": {"field": "sales", "type": "quantitative", "scale": {"domain": [0, 10]}},
        },
        "usermeta": {
            "source": "synthetic.diff",
            "unit": "sales",
            "claim": "Recorded sales vary across these weeks.",
            "user_requested_scale_override": True,
        },
    }


def _frame(values=(4, 5, 6)):
    return pd.DataFrame({"week": ["W1", "W2", "W3"], "sales": list(values)})


def _reports():
    spec = _spec()
    return (
        audit_spec(spec, data=_frame((4, 5, 6))),
        audit_spec(spec, data=_frame((4, 5, 15))),
    )


def _write(tmp_path, before, after):
    old = tmp_path / "before.json"
    new = tmp_path / "after.json"
    old.write_text(json.dumps(before.to_dict()), encoding="utf-8")
    new.write_text(json.dumps(after.to_dict()), encoding="utf-8")
    return str(old), str(new)


def _rebind(report):
    report.report_binding = build_report_binding(
        report, report.input_binding,
        audit_profile=report.report_binding.audit_profile,
    )


def _item(rule, severity, msg, field=None, suggestion=None):
    return AuditFinding(rule_id=rule, severity=severity,
                        message=msg, field=field, suggestion=suggestion)


def test_real_data_drift_pass_to_warning_shows_both_input_and_finding_changes():
    before, after = _reports()
    diff = build_audit_report_diff(before, after)
    assert diff["before"]["verdict"] == "READY"
    assert diff["after"]["verdict"] == "REVIEW"
    assert diff["input_changes"] == {
        "subject_changed": False,
        "data_changed": True,
        "claim_changed": False,
        "tool_version_changed": False,
        "profile_changed": False,
    }
    assert diff["has_regressions"]
    assert diff["counts"]["regressions"] >= 1
    assert any(
        item["rule_id"] == "visual.scale.clipped_data"
        and item["direction"] == "worsened"
        and item["before"]["severity"] == "PASS"
        and item["after"]["severity"] == "WARN"
        for item in diff["findings_changed"]
    )
    assert diff["type"] == "chart_contract.audit_report_diff"
    assert diff["schema_version"] == "1.0"


def test_reverse_diff_records_resolution_without_false_regression():
    before, after = _reports()
    diff = build_audit_report_diff(after, before)
    assert diff["after"]["verdict"] == "READY"
    assert diff["has_improvements"]
    assert not diff["has_regressions"]
    assert any(item["direction"] == "improved" for item in diff["findings_changed"])


def test_identical_reports_and_reordered_findings_have_no_changes():
    before, _ = _reports()
    same = deepcopy(before)
    same.findings.reverse()
    _rebind(same)
    diff = build_audit_report_diff(before, same)
    assert diff["counts"] == {
        "added": 0, "resolved": 0, "changed": 0,
        "regressions": 0, "improvements": 0,
    }
    assert not diff["verdict_changed"]
    assert not any(diff["input_changes"].values())
    assert diff["before"]["report_sha256"] != diff["after"]["report_sha256"]


def test_duplicate_identical_findings_are_multiset_matched():
    before, _ = _reports()
    after = deepcopy(before)
    extra = _item("custom.experiment", "WARN", "Repeated check.", field="encoding.y")
    before.findings.extend([extra, deepcopy(extra)])
    after.findings.append(deepcopy(extra))
    _rebind(before)
    _rebind(after)
    diff = build_audit_report_diff(before, after)
    assert diff["counts"]["resolved"] == 1
    assert diff["counts"]["added"] == 0
    assert diff["findings_resolved"][0]["rule_id"] == "custom.experiment"
    assert diff["findings_resolved"][0]["field"] == "encoding.y"


def test_same_rule_and_field_detail_change_is_not_fake_severity_change():
    before, _ = _reports()
    after = deepcopy(before)
    before.findings.append(_item("custom.axis", "WARN", "Old explanation.", field="encoding.y"))
    after.findings.append(_item("custom.axis", "WARN", "New explanation.", field="encoding.y"))
    _rebind(before)
    _rebind(after)
    diff = build_audit_report_diff(before, after)
    change = next(item for item in diff["findings_changed"]
                  if item["rule_id"] == "custom.axis")
    assert change["direction"] == "unchanged"
    assert change["severity_changed"] is False
    assert change["details_changed"] is True
    assert not diff["has_regressions"]


def test_changed_field_is_add_and_resolve_not_invented_severity_transition():
    before, _ = _reports()
    after = deepcopy(before)
    before.findings.append(_item("custom.scope", "WARN", "One.", field="encoding.x"))
    after.findings.append(_item("custom.scope", "FAIL", "Two.", field="encoding.y"))
    _rebind(before)
    _rebind(after)
    diff = build_audit_report_diff(before, after)
    assert [x["field"] for x in diff["findings_resolved"]] == ["encoding.x"]
    assert [x["field"] for x in diff["findings_added"]] == ["encoding.y"]
    assert not [x for x in diff["findings_changed"] if x["rule_id"] == "custom.scope"]


def test_new_pass_does_not_count_as_regression_and_new_fail_does():
    before, _ = _reports()
    after = deepcopy(before)
    after.findings.extend([
        _item("custom.passed", "PASS", "New passing check."),
        _item("custom.failed", "FAIL", "New failing check."),
    ])
    _rebind(after)
    diff = build_audit_report_diff(before, after)
    assert diff["counts"]["added"] == 2
    assert diff["counts"]["regressions"] == 1
    assert diff["has_regressions"]


def test_policy_drift_is_separate_from_changes_in_results():
    before, _ = _reports()
    after = deepcopy(before)
    manifest = deepcopy(get_profile_manifest().to_dict())
    manifest["rules"][0]["trigger"] = "Changed policy for historical diff example."
    after.report_binding = build_report_binding(
        after, after.input_binding,
        audit_profile=build_audit_profile_binding(manifest),
    )
    # These are validly bound reports, but have distinct historical policies.
    bound_report_from_dict(after.to_dict())
    diff = build_audit_report_diff(before, after)
    assert diff["input_changes"]["profile_changed"] is True
    assert diff["input_changes"]["data_changed"] is False
    assert diff["counts"]["changed"] == 0
    assert "CAUTION: Audit policy differs" in format_audit_diff_text(diff)


def test_tool_version_drift_not_called_policy_drift():
    before, _ = _reports()
    after = deepcopy(before)
    after.input_binding = build_input_binding(
        subject=_spec(), subject_kind="spec",
        data=_frame((4, 5, 6)), claim=_spec()["usermeta"]["claim"],
        tool_version="0.1.7",
    )
    _rebind(after)
    diff = build_audit_report_diff(before, after)
    assert diff["input_changes"]["tool_version_changed"]
    assert not diff["input_changes"]["profile_changed"]
    assert diff["counts"]["regressions"] == 0


def test_spec_and_claim_changes_are_distinguished_from_data_change():
    before, _ = _reports()
    altered_spec = deepcopy(_spec())
    altered_spec["title"] = "Updated weekly sales trend"
    altered_spec["usermeta"]["claim"] = "Recorded sales were inspected by reporting week."
    after = audit_spec(altered_spec, data=_frame((4, 5, 6)))
    diff = build_audit_report_diff(before, after)
    assert diff["input_changes"]["subject_changed"]
    assert diff["input_changes"]["claim_changed"]
    assert not diff["input_changes"]["data_changed"]


def test_mismatched_subject_kind_rejected_without_claiming_comparability():
    before, _ = _reports()
    chart = Chart.trend(
        data=_frame(), x="week", y="sales",
        claim="Recorded sales vary by reporting week.",
        source="synthetic.diff", unit="sales", title="Recorded sales",
    )
    with pytest.raises(ValueError, match="matching subject kinds"):
        build_audit_report_diff(before, chart.audit())


def test_json_cli_outputs_deterministic_machine_readable_diff(tmp_path, capsys):
    before, after = _reports()
    old, new = _write(tmp_path, before, after)
    args = ["audit", "diff", old, new, "--format", "json"]
    assert main(args) == 0
    first = capsys.readouterr().out
    assert main(args) == 0
    assert capsys.readouterr().out == first
    payload = json.loads(first)
    assert payload["before"]["verdict"] == "READY"
    assert payload["after"]["verdict"] == "REVIEW"
    assert payload["input_changes"]["data_changed"]
    assert payload["has_regressions"]


def test_text_cli_formats_new_and_resolved_and_provenance(tmp_path, capsys):
    before, after = _reports()
    old, new = _write(tmp_path, before, after)
    assert main(["audit", "diff", old, new]) == 0
    text = capsys.readouterr().out
    assert "Verdict: READY -> REVIEW" in text
    assert "Data: CHANGED" in text
    assert "Audit policy: SAME" in text
    assert "visual.scale.clipped_data" in text
    assert "Historical diff only" in text


def test_optional_regression_exit_code_and_output_file(tmp_path, capsys):
    before, after = _reports()
    old, new = _write(tmp_path, before, after)
    out = tmp_path / "diff.json"
    assert main(["audit", "diff", old, new, "--format", "json",
                 "--out", str(out), "--fail-on-regression"]) == 1
    assert json.loads(out.read_text())["has_regressions"]
    assert "saved to" in capsys.readouterr().out
    assert main(["audit", "diff", new, old, "--fail-on-regression"]) == 0


@pytest.mark.parametrize("alter", [
    lambda p: p.update({"schema_version": "0.3"}),
    lambda p: p["findings"][0].update({"message": "Tampered"}),
    lambda p: p.update({"verdict": "BLOCK"}),
    lambda p: p["input_binding"].update({"data_sha256": "f" * 64}),
    lambda p: p["report_binding"].update({"report_sha256": "1" * 64}),
])
def test_invalid_legacy_or_tampered_saved_report_fails_closed(tmp_path, alter):
    before, after = _reports()
    payload = before.to_dict()
    alter(payload)
    old = tmp_path / "bad.json"
    new = tmp_path / "after.json"
    old.write_text(json.dumps(payload), encoding="utf-8")
    new.write_text(json.dumps(after.to_dict()), encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main(["audit", "diff", str(old), str(new)])
    assert exc.value.code == 2


def test_json_malformed_missing_or_wrong_suffix_rejected(tmp_path):
    before, after = _reports()
    old, new = _write(tmp_path, before, after)
    bad = tmp_path / "bad.json"
    bad.write_text("{broken", encoding="utf-8")
    for source in (str(bad), str(tmp_path / "missing.json"), str(tmp_path / "wrong.csv")):
        with pytest.raises(SystemExit) as exc:
            main(["audit", "diff", source, new])
        assert exc.value.code == 2


def test_cli_rejects_mixed_subject_kinds(tmp_path):
    before, _ = _reports()
    chart = Chart.trend(
        data=_frame(), x="week", y="sales",
        claim="Recorded sales vary by reporting week.",
        source="synthetic.diff", unit="sales", title="Recorded sales",
    )
    old, new = _write(tmp_path, before, chart.audit())
    with pytest.raises(SystemExit) as exc:
        main(["audit", "diff", old, new])
    assert exc.value.code == 2
