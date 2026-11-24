"""Deterministic comparisons between internally valid saved schema-0.4 audits.

A report diff is a historical comparison, not a fresh audit or a judgment that
changed findings are caused by the data. Input/policy changes are independent
signals; neither audit hash nor profile hash authenticates its producer.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from typing import Any

from .audit import FAIL, PASS, WARN, AuditFinding
from .input_binding import BoundAuditReport

AUDIT_DIFF_TYPE = "chart_contract.audit_report_diff"
AUDIT_DIFF_SCHEMA_VERSION = "1.0"
_SEVERITY_RANK = {PASS: 0, WARN: 1, FAIL: 2}
_FIELDS = ("rule_id", "field", "severity", "message", "suggestion")


def _identity(finding: AuditFinding) -> tuple[str, str | None, str, str, str | None]:
    return (finding.rule_id, finding.field, finding.severity, finding.message, finding.suggestion)


def _sort_key(identity: tuple[str, str | None, str, str, str | None]) -> tuple:
    rule_id, field, severity, message, suggestion = identity
    return (rule_id, field or "", _SEVERITY_RANK[severity], message, suggestion or "")


def _finding(identity: tuple[str, str | None, str, str, str | None]) -> dict[str, Any]:
    return dict(zip(_FIELDS, identity))


def _expand(counts: Counter[tuple]) -> list[tuple]:
    return [identity for identity in sorted(counts, key=_sort_key)
            for _ in range(counts[identity])]


def _pair_findings(
    before: Iterable[AuditFinding],
    after: Iterable[AuditFinding],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Cancel identical findings (including duplicates), then match by rule+field.

    Same-severity matches are paired first to avoid incorrectly treating a
    message change as a severity regression. Remaining instances are matched
    by deterministic severity/message order. A changed field is an addition
    and removal rather than an invented one-to-one correspondence.
    """
    old_count = Counter(_identity(item) for item in before)
    new_count = Counter(_identity(item) for item in after)
    unmatched_old = old_count - new_count
    unmatched_new = new_count - old_count
    old_groups: dict[tuple[str, str | None], list[tuple]] = defaultdict(list)
    new_groups: dict[tuple[str, str | None], list[tuple]] = defaultdict(list)
    for identity in _expand(unmatched_old):
        old_groups[(identity[0], identity[1])].append(identity)
    for identity in _expand(unmatched_new):
        new_groups[(identity[0], identity[1])].append(identity)

    added: list[dict[str, Any]] = []
    resolved: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []
    for key in sorted(set(old_groups) | set(new_groups), key=lambda k: (k[0], k[1] or "")):
        originals = old_groups.get(key, [])
        candidates = new_groups.get(key, [])
        pairs: list[tuple[tuple, tuple]] = []

        # Same severity, different message/suggestion: change in explanation.
        for severity in (PASS, WARN, FAIL):
            same_old = [item for item in originals if item[2] == severity]
            same_new = [item for item in candidates if item[2] == severity]
            paired = min(len(same_old), len(same_new))
            pairs.extend(zip(same_old[:paired], same_new[:paired]))
            originals = [item for item in originals if item[2] != severity] + same_old[paired:]
            candidates = [item for item in candidates if item[2] != severity] + same_new[paired:]

        pair_count = min(len(originals), len(candidates))
        pairs.extend(zip(originals[:pair_count], candidates[:pair_count]))
        resolved.extend(_finding(item) for item in originals[pair_count:])
        added.extend(_finding(item) for item in candidates[pair_count:])
        for old, new in pairs:
            change = _SEVERITY_RANK[new[2]] - _SEVERITY_RANK[old[2]]
            changed.append({
                "rule_id": key[0],
                "field": key[1],
                "before": _finding(old),
                "after": _finding(new),
                "severity_changed": old[2] != new[2],
                "details_changed": old[3:] != new[3:],
                "direction": "worsened" if change > 0 else "improved" if change < 0 else "unchanged",
            })
    return added, resolved, changed


def build_audit_report_diff(
    before: BoundAuditReport, after: BoundAuditReport,
) -> dict[str, Any]:
    """Compare two *already verified* bound report objects.

    Callers loading JSON should validate both with bound_report_from_dict()
    first. The diff does not re-run the underlying audit or verify live source
    data; it compares exactly what the saved reports attest.
    """
    old_input, new_input = before.input_binding, after.input_binding
    old_report, new_report = before.report_binding, after.report_binding
    if any(binding is None for binding in (old_input, new_input, old_report, new_report)):
        raise ValueError("Audit report diff requires two schema-0.4 reports with durable bindings.")
    if old_input.subject_kind != new_input.subject_kind:
        raise ValueError(
            "Audit report diff requires matching subject kinds; "
            f"got {old_input.subject_kind!r} and {new_input.subject_kind!r}."
        )
    input_changes = {
        "subject_changed": old_input.subject_sha256 != new_input.subject_sha256,
        "data_changed": old_input.data_sha256 != new_input.data_sha256,
        "claim_changed": old_input.claim_sha256 != new_input.claim_sha256,
        "tool_version_changed": old_input.tool_version != new_input.tool_version,
        "profile_changed": old_report.audit_profile != new_report.audit_profile,
    }
    added, resolved, changed = _pair_findings(before.findings, after.findings)
    regressions = sum(item["severity"] in (WARN, FAIL) for item in added) + sum(
        item["direction"] == "worsened" for item in changed
    )
    improvements = sum(item["severity"] in (WARN, FAIL) for item in resolved) + sum(
        item["direction"] == "improved" for item in changed
    )
    return {
        "schema_version": AUDIT_DIFF_SCHEMA_VERSION,
        "type": AUDIT_DIFF_TYPE,
        "subject_kind": old_input.subject_kind,
        "before": {
            "verdict": before.verdict,
            "summary": before.summary(),
            "subject_sha256": old_input.subject_sha256,
            "data_sha256": old_input.data_sha256,
            "claim_sha256": old_input.claim_sha256,
            "tool_version": old_input.tool_version,
            "profile": old_report.audit_profile.to_dict(),
            "report_sha256": old_report.report_sha256,
        },
        "after": {
            "verdict": after.verdict,
            "summary": after.summary(),
            "subject_sha256": new_input.subject_sha256,
            "data_sha256": new_input.data_sha256,
            "claim_sha256": new_input.claim_sha256,
            "tool_version": new_input.tool_version,
            "profile": new_report.audit_profile.to_dict(),
            "report_sha256": new_report.report_sha256,
        },
        "verdict_changed": before.verdict != after.verdict,
        "input_changes": input_changes,
        "findings_added": added,
        "findings_resolved": resolved,
        "findings_changed": changed,
        "counts": {
            "added": len(added),
            "resolved": len(resolved),
            "changed": len(changed),
            "regressions": regressions,
            "improvements": improvements,
        },
        "has_regressions": regressions > 0,
        "has_improvements": improvements > 0,
        "interpretation": (
            "Historical finding changes are not proof of improving or worsening analytical truth. "
            "When profile_changed is true, findings may differ because audit policy changed; "
            "when subject_changed is true, the chart/spec or inline source data changed. "
            "Source evidence was not re-audited. Input/report hashes detect drift, not authorship."
        ),
    }


def format_audit_diff_text(diff: dict[str, Any]) -> str:
    """Stable agent-readable text, with explicit drift and change categories."""
    flags = diff["input_changes"]
    counts = diff["counts"]
    lines = [
        f"Verdict: {diff['before']['verdict']} -> {diff['after']['verdict']}",
        f"Before summary: {diff['before']['summary']}",
        f"After summary: {diff['after']['summary']}",
        "Input/policy identities:",
    ]
    for key, name in (
        ("subject_changed", "Subject"),
        ("data_changed", "Data"),
        ("claim_changed", "Claim"),
        ("tool_version_changed", "Tool version"),
        ("profile_changed", "Audit policy"),
    ):
        lines.append(f"  {name}: {'CHANGED' if flags[key] else 'SAME'}")
    lines.extend([
        f"Findings: {counts['added']} added, {counts['resolved']} resolved, "
        f"{counts['changed']} changed",
        f"Severity changes: {counts['regressions']} regression(s), "
        f"{counts['improvements']} improvement(s)",
    ])
    for heading, findings in (
        ("Added findings", diff["findings_added"]),
        ("Resolved findings", diff["findings_resolved"]),
    ):
        lines.append(f"{heading}:")
        if not findings:
            lines.append("  (none)")
        for item in findings:
            label = item["rule_id"] + (f" [{item['field']}]" if item["field"] else "")
            lines.append(f"  {item['severity']} {label}: {item['message']}")
    lines.append("Changed findings:")
    if not diff["findings_changed"]:
        lines.append("  (none)")
    for item in diff["findings_changed"]:
        label = item["rule_id"] + (f" [{item['field']}]" if item["field"] else "")
        lines.append(
            f"  {label}: {item['before']['severity']} -> {item['after']['severity']} "
            f"({item['direction']}); "
            f"{item['before']['message']} -> {item['after']['message']}"
        )
    if flags["profile_changed"]:
        lines.append("CAUTION: Audit policy differs; a greener verdict need not reflect better evidence.")
    lines.append("Historical diff only; this did not re-audit source data or authenticate saved reports.")
    return "\n".join(lines)
