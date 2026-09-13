"""Mechanical diffs for saved chart-contract audit profile manifests."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .profiles import build_audit_profile_binding

PROFILE_DIFF_SCHEMA_VERSION = "1.0"
PROFILE_DIFF_TYPE = "chart_contract.audit_profile_diff"


@dataclass(frozen=True)
class FieldChange:
    field: str
    before: Any
    after: Any

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuleChange:
    rule_id: str
    changes: tuple[FieldChange, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.rule_id, "changes": [change.to_dict() for change in self.changes]}


@dataclass(frozen=True)
class ProfileDiff:
    before_profile: str
    after_profile: str
    before_binding: dict[str, Any]
    after_binding: dict[str, Any]
    profile_changes: tuple[FieldChange, ...]
    rules_added: tuple[dict[str, Any], ...]
    rules_removed: tuple[dict[str, Any], ...]
    rules_changed: tuple[RuleChange, ...]
    rule_order_changed: bool
    before_rule_order: tuple[str, ...]
    after_rule_order: tuple[str, ...]
    tool_metadata_changed: bool

    @property
    def semantic_changed(self) -> bool:
        return self.before_binding != self.after_binding

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PROFILE_DIFF_SCHEMA_VERSION,
            "type": PROFILE_DIFF_TYPE,
            "semantic_changed": self.semantic_changed,
            "tool_metadata_changed": self.tool_metadata_changed,
            "before": {"profile": self.before_profile, "binding": self.before_binding},
            "after": {"profile": self.after_profile, "binding": self.after_binding},
            "profile_changes": [change.to_dict() for change in self.profile_changes],
            "rules_added": list(self.rules_added),
            "rules_removed": list(self.rules_removed),
            "rules_changed": [change.to_dict() for change in self.rules_changed],
            "rule_order_changed": self.rule_order_changed,
            "before_rule_order": list(self.before_rule_order),
            "after_rule_order": list(self.after_rule_order),
            "compatibility_judgment": None,
        }


def build_profile_diff(before: dict[str, Any], after: dict[str, Any]) -> ProfileDiff:
    before_binding = build_audit_profile_binding(before).to_dict()
    after_binding = build_audit_profile_binding(after).to_dict()
    before_profile = dict(before["profile"])
    after_profile = dict(after["profile"])
    profile_changes = tuple(
        FieldChange(field=field, before=before_profile.get(field), after=after_profile.get(field))
        for field in sorted(set(before_profile) | set(after_profile))
        if before_profile.get(field) != after_profile.get(field)
    )
    before_rules = list(before["rules"])
    after_rules = list(after["rules"])
    before_by_id = {str(rule["id"]): dict(rule) for rule in before_rules}
    after_by_id = {str(rule["id"]): dict(rule) for rule in after_rules}
    added_ids = sorted(set(after_by_id) - set(before_by_id))
    removed_ids = sorted(set(before_by_id) - set(after_by_id))
    shared_ids = sorted(set(before_by_id) & set(after_by_id))
    changed: list[RuleChange] = []
    for rule_id in shared_ids:
        before_rule = before_by_id[rule_id]
        after_rule = after_by_id[rule_id]
        fields = sorted((set(before_rule) | set(after_rule)) - {"id"})
        changes = tuple(
            FieldChange(field=field, before=before_rule.get(field), after=after_rule.get(field))
            for field in fields
            if before_rule.get(field) != after_rule.get(field)
        )
        if changes:
            changed.append(RuleChange(rule_id=rule_id, changes=changes))
    before_order = tuple(str(rule["id"]) for rule in before_rules)
    after_order = tuple(str(rule["id"]) for rule in after_rules)
    return ProfileDiff(
        before_profile=str(before_profile["name"]),
        after_profile=str(after_profile["name"]),
        before_binding=before_binding,
        after_binding=after_binding,
        profile_changes=profile_changes,
        rules_added=tuple(after_by_id[rule_id] for rule_id in added_ids),
        rules_removed=tuple(before_by_id[rule_id] for rule_id in removed_ids),
        rules_changed=tuple(changed),
        rule_order_changed=before_order != after_order,
        before_rule_order=before_order,
        after_rule_order=after_order,
        tool_metadata_changed=before.get("tool") != after.get("tool"),
    )
