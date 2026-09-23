from __future__ import annotations

import json
from copy import deepcopy

import pytest

from chart_contract.cli import main
from chart_contract.profiles import get_profile_manifest


def test_cli_profile_show_json(capsys) -> None:
    code = main(["profile", "show", "audit-v0.2", "--json"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["type"] == "chart_contract.audit_profile_manifest"
    assert payload["profile"]["name"] == "audit-v0.2"
    assert payload["rule_count"] == 51
    assert payload["scientific_validation"] is False
    assert payload["automatic_adjudication"] is False


def test_cli_profile_show_text_preserves_boundary(capsys) -> None:
    code = main(["profile", "show"])

    assert code == 0
    output = capsys.readouterr().out
    assert "Profile: audit-v0.2" in output
    assert "Rules: 51" in output
    assert "Scientific validation: false" in output
    assert "Automatic adjudication: false" in output
    assert "claim.causal_support" in output


def test_cli_profile_diff_json_reports_semantic_change(tmp_path, capsys) -> None:
    before = get_profile_manifest().to_dict()
    after = deepcopy(before)
    after["rules"][0]["trigger"] = "Changed trigger for CLI regression coverage."

    before_path = tmp_path / "before.json"
    after_path = tmp_path / "after.json"
    before_path.write_text(json.dumps(before), encoding="utf-8")
    after_path.write_text(json.dumps(after), encoding="utf-8")

    code = main(["profile", "diff", str(before_path), str(after_path), "--json"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["type"] == "chart_contract.audit_profile_diff"
    assert payload["semantic_changed"] is True
    assert payload["compatibility_judgment"] is None
    assert payload["rules_changed"][0]["id"] == before["rules"][0]["id"]


def test_cli_profile_rejects_unknown_profile(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["profile", "show", "not-a-profile"])

    assert exc_info.value.code == 2
    assert "Unsupported profile" in capsys.readouterr().err
