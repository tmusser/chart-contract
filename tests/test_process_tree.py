from __future__ import annotations

import pandas as pd
import pytest

from chart_contract import Chart
from chart_contract.process_tree import process_tree_layout_records, process_tree_summary


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "step_id": ["start", "review", "approve", "revise", "ship"],
            "parent_id": [None, "start", "review", "review", "approve"],
            "step": [
                "Request received",
                "Review request",
                "Approve",
                "Revise",
                "Ship",
            ],
            "branch": [None, None, "Yes", "No", None],
        }
    )


def _severities(report):
    return {finding.rule_id: finding.severity for finding in report.findings}


def test_process_tree_summary_preserves_root_and_depth() -> None:
    summary = process_tree_summary(
        _frame(),
        node="step_id",
        parent="parent_id",
        label="step",
        branch="branch",
    )

    assert summary.root == "start"
    assert summary.node_count == 5
    assert summary.edge_count == 4
    assert summary.max_depth == 3


def test_process_tree_layout_is_top_down_and_respects_sibling_order() -> None:
    nodes, connectors, arrows, branches = process_tree_layout_records(
        _frame(),
        node="step_id",
        parent="parent_id",
        label="step",
        branch="branch",
    )
    by_id = {record["node_id"]: record for record in nodes}

    assert by_id["start"]["y"] < by_id["review"]["y"] < by_id["approve"]["y"]
    assert by_id["approve"]["x"] < by_id["revise"]["x"]
    assert len(connectors) == 16
    assert len(arrows) == 4
    assert [record["label"] for record in branches] == ["Yes", "No"]


def test_process_tree_renders_as_layered_flowchart() -> None:
    chart = Chart.process_tree(
        data=_frame(),
        node="step_id",
        parent="parent_id",
        label="step",
        branch="branch",
        claim="Requests move from intake through review to either revision or approval.",
        source="synthetic.approval_process",
        title="Request approval flow",
    )

    spec = chart.to_vega_lite()
    mark_types = [layer["mark"]["type"] for layer in spec["layer"]]

    assert chart.intent == "process_tree"
    assert mark_types == ["line", "point", "rect", "text", "text"]
    assert spec["width"] == 760
    assert spec["usermeta"]["chart_contract_intent"] == "process_tree"
    assert spec["usermeta"]["process_tree"]["root"] == "start"
    assert spec["usermeta"]["process_tree"]["node_count"] == 5
    assert spec["usermeta"]["process_tree"]["edge_count"] == 4
    assert "top-down rooted tree" in spec["usermeta"]["process_tree"]["layout"]


def test_valid_process_tree_contract_is_ready() -> None:
    report = Chart.process_tree(
        data=_frame(),
        node="step_id",
        parent="parent_id",
        label="step",
        branch="branch",
        claim="Requests move through the documented approval flow.",
        source="synthetic.approval_process",
        title="Request approval flow",
    ).audit()

    assert report.verdict == "READY"
    assert _severities(report)["data.process_tree.node_unique"] == "PASS"
    assert _severities(report)["data.process_tree.root"] == "PASS"
    assert _severities(report)["data.process_tree.parent_reference"] == "PASS"
    assert _severities(report)["data.process_tree.acyclic"] == "PASS"
    assert _severities(report)["visual.process_tree.structure"] == "PASS"


def test_process_tree_blocks_duplicate_nodes() -> None:
    frame = _frame()
    frame.loc[4, "step_id"] = "approve"

    report = Chart.process_tree(
        data=frame,
        node="step_id",
        parent="parent_id",
        label="step",
        claim="Documented approval flow.",
        source="synthetic.approval_process",
        title="Request approval flow",
    ).audit()

    assert report.verdict == "BLOCK"
    assert _severities(report)["data.process_tree.node_unique"] == "FAIL"


def test_process_tree_blocks_unknown_parent() -> None:
    frame = _frame()
    frame.loc[4, "parent_id"] = "missing"

    report = Chart.process_tree(
        data=frame,
        node="step_id",
        parent="parent_id",
        label="step",
        claim="Documented approval flow.",
        source="synthetic.approval_process",
        title="Request approval flow",
    ).audit()

    assert report.verdict == "BLOCK"
    assert _severities(report)["data.process_tree.parent_reference"] == "FAIL"


def test_process_tree_blocks_multiple_roots() -> None:
    frame = _frame()
    frame.loc[3, "parent_id"] = None

    report = Chart.process_tree(
        data=frame,
        node="step_id",
        parent="parent_id",
        label="step",
        claim="Documented approval flow.",
        source="synthetic.approval_process",
        title="Request approval flow",
    ).audit()

    assert report.verdict == "BLOCK"
    assert _severities(report)["data.process_tree.root"] == "FAIL"


def test_process_tree_blocks_cycles() -> None:
    frame = _frame()
    frame.loc[0, "parent_id"] = "ship"
    frame.loc[4, "parent_id"] = None
    frame.loc[1, "parent_id"] = "revise"
    frame.loc[3, "parent_id"] = "review"

    report = Chart.process_tree(
        data=frame,
        node="step_id",
        parent="parent_id",
        label="step",
        claim="Documented approval flow.",
        source="synthetic.approval_process",
        title="Request approval flow",
    ).audit()

    assert report.verdict == "BLOCK"
    assert _severities(report)["data.process_tree.acyclic"] == "FAIL"


def test_invalid_process_tree_refuses_to_render() -> None:
    frame = _frame()
    frame.loc[4, "parent_id"] = "missing"

    chart = Chart.process_tree(
        data=frame,
        node="step_id",
        parent="parent_id",
        label="step",
        claim="Documented approval flow.",
        source="synthetic.approval_process",
        title="Request approval flow",
    )

    with pytest.raises(ValueError, match="parent reference"):
        chart.to_vega_lite()
