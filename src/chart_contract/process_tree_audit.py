"""Audit rules for rooted process-tree charts."""

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
from .process_tree import process_tree_summary


def audit_process_tree_chart(chart: Any) -> AuditReport:
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
            suggestion="Add a claim that states what the process tree represents.",
            field="claim",
        )

    if source:
        report.add("contract.source.present", PASS, "Source is declared.")
    else:
        report.add(
            "contract.source.present",
            WARN,
            "Source is missing; provenance should be visible.",
            suggestion="Add a source such as a workflow definition, policy, or process owner.",
            field="source",
        )

    declared = {
        "node": getattr(chart, "node", None),
        "parent": getattr(chart, "parent", None),
        "label": getattr(chart, "label", None),
    }
    if getattr(chart, "branch", None):
        declared["branch"] = chart.branch

    undeclared = [name for name, field in declared.items() if not isinstance(field, str) or not field]
    if undeclared:
        report.add(
            "data.process_tree.columns",
            FAIL,
            f"Process tree is missing field declaration(s): {', '.join(undeclared)}.",
            suggestion="Declare node, parent, label, and optional branch columns.",
        )
        return _finish_common_rules(report, chart, claim, title, caveat)

    missing = [field for field in declared.values() if field not in chart.data.columns]
    if missing:
        report.add(
            "data.process_tree.columns",
            FAIL,
            f"Required process-tree column(s) are missing: {', '.join(missing)}.",
            suggestion="Add the missing columns or update the chart contract.",
            field=missing[0],
        )
        return _finish_common_rules(report, chart, claim, title, caveat)

    report.add(
        "data.process_tree.columns",
        PASS,
        "Node, parent, label, and optional branch columns are present.",
    )

    if chart.data.empty:
        report.add(
            "data.not_empty",
            WARN,
            "Chart data is empty; the process tree has no nodes to render.",
        )
        return _finish_common_rules(report, chart, claim, title, caveat)
    report.add("data.not_empty", PASS, "Chart data is not empty.")

    node = chart.node
    parent = chart.parent
    label = chart.label

    identifiers = chart.data[node]
    if identifiers.isna().any():
        report.add(
            "data.process_tree.node_unique",
            FAIL,
            "Process-tree node identifiers contain null values.",
            suggestion="Provide one non-null identifier per node.",
            field=node,
        )
    elif identifiers.duplicated().any():
        report.add(
            "data.process_tree.node_unique",
            FAIL,
            "Process-tree node identifiers must be unique.",
            suggestion="Deduplicate node identifiers before rendering.",
            field=node,
        )
    else:
        report.add(
            "data.process_tree.node_unique",
            PASS,
            "Process-tree node identifiers are non-null and unique.",
        )

    labels = chart.data[label]
    if labels.isna().any() or any(not str(value).strip() for value in labels.tolist()):
        report.add(
            "data.process_tree.labels",
            FAIL,
            "Process-tree labels must be non-null and non-empty.",
            suggestion="Give every node a readable label.",
            field=label,
        )
    else:
        report.add(
            "data.process_tree.labels",
            PASS,
            "Every process-tree node has a readable label.",
        )

    parents = chart.data[parent]
    roots = parents.map(_is_root_parent)
    root_count = int(roots.sum())
    if root_count != 1:
        report.add(
            "data.process_tree.root",
            FAIL,
            f"Process tree requires exactly one root; found {root_count}.",
            suggestion="Leave parent empty for exactly one root node.",
            field=parent,
        )
    else:
        report.add(
            "data.process_tree.root",
            PASS,
            "Process tree has exactly one root.",
        )

    node_values = set(identifiers.dropna().tolist())
    parent_values = [
        value for value in parents.tolist()
        if not _is_root_parent(value)
    ]
    unknown = sorted({str(value) for value in parent_values if value not in node_values})
    if unknown:
        report.add(
            "data.process_tree.parent_reference",
            FAIL,
            "Process-tree parent reference(s) do not exist: " + ", ".join(unknown) + ".",
            suggestion="Point every non-root node at an existing node identifier.",
            field=parent,
        )
    else:
        report.add(
            "data.process_tree.parent_reference",
            PASS,
            "Every non-root parent reference resolves to an existing node.",
        )

    if not report.has_failures:
        try:
            summary = process_tree_summary(
                chart.data,
                node=node,
                parent=parent,
                label=label,
                branch=chart.branch,
            )
        except ValueError as exc:
            message = str(exc)
            if "cycle" in message.lower():
                report.add(
                    "data.process_tree.acyclic",
                    FAIL,
                    message,
                    suggestion="Remove the circular parent relationship so every path terminates at the root.",
                    field=parent,
                )
            else:
                report.add(
                    "data.process_tree.acyclic",
                    FAIL,
                    message,
                    suggestion="Repair the rooted-tree structure before rendering.",
                    field=parent,
                )
        else:
            report.add(
                "data.process_tree.acyclic",
                PASS,
                "Process-tree parent relationships are acyclic.",
            )
            report.add(
                "visual.process_tree.structure",
                PASS,
                (
                    "First-party process-tree layout preserves rooted topology and explicit edge direction "
                    f"for {summary.node_count} node(s) and {summary.edge_count} edge(s)."
                ),
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
            suggestion="Use a specific title or concrete process-map claim.",
            field="title",
        )
    else:
        report.add("labels.title.quality", PASS, "Title is specific enough to support interpretation.")

    report.add(
        "visual.intent.match",
        PASS,
        "Process-tree visual form matches the declared chart intent.",
    )

    decorative_terms = find_decorative_terms(chart.metadata or {})
    if decorative_terms:
        report.add(
            "visual.integrity.decoration",
            WARN,
            f"Decorative metadata hints at distracting encodings: {', '.join(decorative_terms)}.",
            suggestion="Keep the process map focused on nodes, branches, and labels.",
        )
    else:
        report.add(
            "visual.integrity.decoration",
            PASS,
            "No decorative metadata suggests chartjunk-like encodings.",
        )
    return report


def _is_root_parent(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    try:
        return bool(__import__("pandas").isna(value))
    except (TypeError, ValueError):
        return False
