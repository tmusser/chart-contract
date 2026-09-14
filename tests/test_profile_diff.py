from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from chart_contract.profile_diff import build_profile_diff
from chart_contract.profiles import get_profile_manifest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "audit-profile-diff-v1.schema.json"


def test_identical_profiles_have_no_semantic_drift() -> None:
    before = get_profile_manifest().to_dict()
    after = deepcopy(before)

    diff = build_profile_diff(before, after)

    assert diff.semantic_changed is False
    assert diff.tool_metadata_changed is False
    assert diff.profile_changes == ()
    assert diff.rules_added == ()
    assert diff.rules_removed == ()
    assert diff.rules_changed == ()
    assert diff.rule_order_changed is False
    assert diff.to_dict()["compatibility_judgment"] is None


def test_tool_version_only_drift_is_not_semantic_drift() -> None:
    before = get_profile_manifest().to_dict()
    after = deepcopy(before)
    after["tool"]["version"] = "999.0.0"

    diff = build_profile_diff(before, after)

    assert diff.semantic_changed is False
    assert diff.tool_metadata_changed is True
    assert diff.before_binding == diff.after_binding


def test_rule_change_is_reported_and_changes_semantic_identity() -> None:
    before = get_profile_manifest().to_dict()
    after = deepcopy(before)
    after["rules"][0]["known_boundary"] = "Changed boundary for regression coverage."

    diff = build_profile_diff(before, after)

    assert diff.semantic_changed is True
    assert len(diff.rules_changed) == 1
    assert diff.rules_changed[0].rule_id == before["rules"][0]["id"]
    assert [change.field for change in diff.rules_changed[0].changes] == ["known_boundary"]


def test_rule_add_remove_and_order_drift_are_mechanical() -> None:
    before = get_profile_manifest().to_dict()
    after = deepcopy(before)
    removed = after["rules"].pop(0)
    added = deepcopy(after["rules"][0])
    added["id"] = "synthetic.test.rule"
    after["rules"].append(added)
    after["rule_count"] = len(after["rules"])
    after["rules"][0], after["rules"][1] = after["rules"][1], after["rules"][0]

    diff = build_profile_diff(before, after)

    assert diff.semantic_changed is True
    assert [rule["id"] for rule in diff.rules_removed] == [removed["id"]]
    assert [rule["id"] for rule in diff.rules_added] == ["synthetic.test.rule"]
    assert diff.rule_order_changed is True


def test_profile_diff_schema_preserves_no_compatibility_judgment_boundary() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    assert schema["properties"]["type"]["const"] == "chart_contract.audit_profile_diff"
    assert schema["properties"]["compatibility_judgment"]["type"] == "null"
    assert schema["additionalProperties"] is False
