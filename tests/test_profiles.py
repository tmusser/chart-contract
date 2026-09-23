from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

from chart_contract.profiles import (
    DEFAULT_PROFILE,
    PROFILE_BINDING_CANONICALIZATION,
    build_audit_profile_binding,
    get_profile_manifest,
    validate_rule_emission,
)


ROOT = Path(__file__).resolve().parents[1]
DOC_RULES = ROOT / "docs" / "AUDIT_RULES.md"
SCHEMA = ROOT / "schemas" / "audit-profile-v1.schema.json"
RULE_ROW = re.compile(r"^\| `([^`]+)` \|")


def _documented_rule_ids() -> list[str]:
    return [
        match.group(1)
        for line in DOC_RULES.read_text(encoding="utf-8").splitlines()
        if (match := RULE_ROW.match(line))
    ]


def test_profile_manifest_covers_documented_rule_reference_in_order() -> None:
    manifest = get_profile_manifest(DEFAULT_PROFILE)
    manifest_ids = [rule.rule_id for rule in manifest.rules]
    documented_ids = _documented_rule_ids()

    assert len(manifest_ids) == 51
    assert len(manifest_ids) == len(set(manifest_ids))
    assert manifest_ids == documented_ids


def test_profile_manifest_preserves_interpretation_boundary() -> None:
    payload = get_profile_manifest().to_dict()

    assert payload["type"] == "chart_contract.audit_profile_manifest"
    assert payload["profile"]["name"] == "audit-v0.2"
    assert payload["scientific_validation"] is False
    assert payload["automatic_adjudication"] is False
    assert "not scientific validation" in payload["scope_notice"].lower()
    assert payload["not_evaluated"]
    assert payload["rule_count"] == len(payload["rules"])


def test_profile_schema_declares_closed_machine_readable_contract() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["type"]["const"] == "chart_contract.audit_profile_manifest"
    assert schema["properties"]["scientific_validation"]["const"] is False
    assert schema["properties"]["automatic_adjudication"]["const"] is False
    assert schema["additionalProperties"] is False


def test_profile_binding_ignores_tool_version_only_drift() -> None:
    before = get_profile_manifest().to_dict()
    after = deepcopy(before)
    after["tool"]["version"] = "999.0.0"

    assert build_audit_profile_binding(before) == build_audit_profile_binding(after)


def test_profile_binding_changes_when_rule_semantics_change() -> None:
    before = get_profile_manifest().to_dict()
    after = deepcopy(before)
    after["rules"][0]["trigger"] = "Different trigger semantics."

    before_binding = build_audit_profile_binding(before)
    after_binding = build_audit_profile_binding(after)

    assert before_binding.canonicalization == PROFILE_BINDING_CANONICALIZATION
    assert before_binding.profile_manifest_sha256 != after_binding.profile_manifest_sha256


def test_profile_binding_changes_when_allowed_severity_changes() -> None:
    before = get_profile_manifest().to_dict()
    after = deepcopy(before)
    rule = next(rule for rule in after["rules"] if rule["id"] == "data.distribution.sample_size")
    rule["severities"] = ["PASS", "WARN"]

    assert build_audit_profile_binding(before) != build_audit_profile_binding(after)


def test_rule_registry_accepts_only_declared_emissions() -> None:
    validate_rule_emission("data.distribution.sample_size", "PASS")
    validate_rule_emission("data.distribution.sample_size", "WARN")
    validate_rule_emission("data.distribution.sample_size", "FAIL")

    with pytest.raises(ValueError, match="not registered"):
        validate_rule_emission("not.a.rule", "WARN")

    with pytest.raises(ValueError, match="allowed severities"):
        validate_rule_emission("claim.event_without_caveat", "PASS")
