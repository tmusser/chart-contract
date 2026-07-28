"""Audit rules for two-set membership charts."""

from __future__ import annotations

from typing import Any

from .audit import FAIL, PASS, WARN, AuditReport
from .contracts import (
    find_decorative_terms,
    has_causal_language,
    has_declared_causal_evidence,
    implies_filter_or_time_window,
    is_generic_title,
)
from .set_membership import is_binary_membership_series, membership_summary


def audit_set_membership_chart(chart: Any) -> AuditReport:
    report = AuditReport()
    claim = (chart.claim or "").strip()
    source = (chart.source or "").strip()
    caveat = (chart.caveat or "").strip()
    title = (chart.title or claim).strip()

    if claim:
        report.add("contract.claim.present", PASS, "Claim is declared.")
    else:
        report.add(
            "contract.claim.present",
            FAIL,
            "Claim is required for an audited chart.",
            suggestion="Add a claim that states what the set relationship means.",
            field="claim",
        )

    if source:
        report.add("contract.source.present", PASS, "Source is declared.")
    else:
        report.add(
            "contract.source.present",
            WARN,
            "Source is missing; provenance should be visible.",
            suggestion="Add a source such as a table, model, or query identifier.",
            field="source",
        )

    required = {
        "member": getattr(chart, "member", None),
        "set_a": getattr(chart, "set_a", None),
        "set_b": getattr(chart, "set_b", None),
    }
    undeclared = [name for name, field in required.items() if not isinstance(field, str) or not field]
    if undeclared:
        report.add(
            "data.set_membership.columns",
            FAIL,
            f"Set membership chart is missing field declaration(s): {', '.join(undeclared)}.",
            suggestion="Declare member, set_a, and set_b columns.",
        )
        return _finish_common_rules(report, chart, claim, title, caveat)

    missing = [field for field in required.values() if field not in chart.data.columns]
    if missing:
        report.add(
            "data.set_membership.columns",
            FAIL,
            f"Required set membership column(s) are missing: {', '.join(missing)}.",
            suggestion="Add the missing columns or update the chart contract.",
            field=missing[0],
        )
    else:
        report.add(
            "data.set_membership.columns",
            PASS,
            "Member identifier and both membership columns are present.",
        )

    if chart.data.empty:
        report.add(
            "data.not_empty",
            WARN,
            "Chart data is empty; the rendered set relationship will not support the claim.",
        )
    else:
        report.add("data.not_empty", PASS, "Chart data is not empty.")

    member = required["member"]
    set_a = required["set_a"]
    set_b = required["set_b"]
    if not missing:
        identifiers = chart.data[member]
        if identifiers.isna().any():
            report.add(
                "data.set_membership.member_unique",
                FAIL,
                "Member identifiers contain null values.",
                suggestion="Provide one non-null identifier per universe member.",
                field=member,
            )
        elif identifiers.duplicated().any():
            duplicate_count = int(identifiers.duplicated().sum())
            report.add(
                "data.set_membership.member_unique",
                FAIL,
                f"Member identifiers contain {duplicate_count} duplicate row(s), which would overcount regions.",
                suggestion="Deduplicate to one row per universe member before rendering.",
                field=member,
            )
        else:
            report.add(
                "data.set_membership.member_unique",
                PASS,
                "Member identifiers are non-null and unique.",
            )

        invalid_fields = [field for field in (set_a, set_b) if not is_binary_membership_series(chart.data[field])]
        if invalid_fields:
            report.add(
                "data.set_membership.binary",
                FAIL,
                f"Membership column(s) must contain only non-null booleans or integer 0/1 values: {', '.join(invalid_fields)}.",
                suggestion="Convert membership evidence to explicit boolean or 0/1 columns.",
                field=invalid_fields[0],
            )
        else:
            report.add(
                "data.set_membership.binary",
                PASS,
                "Both membership columns are explicit binary evidence.",
            )
            summary = membership_summary(chart.data, set_a=set_a, set_b=set_b)
            report.add(
                "data.set_membership.region_counts",
                PASS,
                (
                    "Set regions reconcile to the declared universe: "
                    f"A-only={summary.a_only}, overlap={summary.overlap}, "
                    f"B-only={summary.b_only}, neither={summary.neither}."
                ),
            )

    report.add(
        "visual.set_membership.area_semantics",
        PASS,
        "The first-party Venn-style renderer declares schematic geometry and makes region counts authoritative.",
    )
    return _finish_common_rules(report, chart, claim, title, caveat)


def _finish_common_rules(
    report: AuditReport,
    chart: Any,
    claim: str,
    title: str,
    caveat: str,
) -> AuditReport:
    if has_causal_language(claim) and not (caveat or has_declared_causal_evidence(chart.metadata)):
        report.add(
            "claim.causal_support",
            WARN,
            "Claim uses causal language without a caveat or causal evidence flag.",
            suggestion="Add a caveat or set metadata['causal_evidence']=True when the evidence supports it.",
            field="claim",
        )
    elif claim:
        report.add("claim.causal_support", PASS, "Claim support language is acceptable.")

    if claim and implies_filter_or_time_window(claim) and not chart.filters:
        report.add(
            "contract.filters.implied",
            WARN,
            "Claim implies a filter or time window that is not explicitly declared.",
            suggestion="Add filters metadata or clarify the scope in the chart contract.",
            field="filters",
        )

    if is_generic_title(title):
        report.add(
            "labels.title.quality",
            WARN,
            "Chart title is missing or generic.",
            suggestion="Use a specific title or a concrete set-relationship claim.",
            field="title",
        )
    else:
        report.add("labels.title.quality", PASS, "Title is specific enough to support interpretation.")

    report.add(
        "visual.intent.match",
        PASS,
        "Set membership visual form matches the declared chart intent.",
    )

    decorative_terms = find_decorative_terms(chart.metadata or {})
    if decorative_terms:
        report.add(
            "visual.integrity.decoration",
            WARN,
            f"Decorative metadata hints at distracting encodings: {', '.join(decorative_terms)}.",
            suggestion="Prefer labeled set regions over decorative effects.",
        )
    else:
        report.add(
            "visual.integrity.decoration",
            PASS,
            "No decorative metadata suggests chartjunk-like encodings.",
        )
    return report
