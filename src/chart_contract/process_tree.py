"""Rooted process-tree validation and deterministic layout helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True, slots=True)
class ProcessTreeSummary:
    """Structural summary for one rooted process tree."""

    root: Any
    node_count: int
    edge_count: int
    max_depth: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "max_depth": self.max_depth,
        }


def process_tree_summary(
    data: pd.DataFrame,
    *,
    node: str,
    parent: str,
    label: str,
    branch: str | None = None,
) -> ProcessTreeSummary:
    """Validate a rooted tree and return structural summary metadata."""

    required = [node, parent, label]
    if branch:
        required.append(branch)
    missing = [field for field in required if field not in data.columns]
    if missing:
        raise ValueError(f"Missing process-tree column(s): {', '.join(missing)}")
    if data.empty:
        raise ValueError("Process tree requires at least one node.")

    node_values = data[node].tolist()
    if data[node].isna().any() or any(
        isinstance(value, str) and not value.strip() for value in node_values
    ):
        raise ValueError("Process-tree node identifiers must be non-null and non-empty.")
    if data[node].duplicated().any():
        raise ValueError("Process-tree node identifiers must be unique.")

    labels = data[label]
    if labels.isna().any() or any(not str(value).strip() for value in labels.tolist()):
        raise ValueError("Process-tree labels must be non-null and non-empty.")

    parents = [_parent_value(value) for value in data[parent].tolist()]
    roots = [node_values[index] for index, value in enumerate(parents) if value is None]
    if len(roots) != 1:
        raise ValueError(f"Process tree requires exactly one root; found {len(roots)}.")

    node_set = set(node_values)
    missing_parents = sorted(
        {str(value) for value in parents if value is not None and value not in node_set}
    )
    if missing_parents:
        raise ValueError(
            "Process-tree parent reference(s) do not exist: "
            + ", ".join(missing_parents)
        )

    parent_by_node = {
        node_values[index]: parents[index]
        for index in range(len(node_values))
    }
    _assert_acyclic(parent_by_node)

    children = {value: [] for value in node_values}
    for child, parent_value in parent_by_node.items():
        if parent_value is not None:
            children[parent_value].append(child)

    root = roots[0]
    depths = _depths(root, children)
    if len(depths) != len(node_values):
        raise ValueError("Every process-tree node must be reachable from the single root.")

    return ProcessTreeSummary(
        root=root,
        node_count=len(node_values),
        edge_count=max(0, len(node_values) - 1),
        max_depth=max(depths.values(), default=0),
    )


def process_tree_layout_records(
    data: pd.DataFrame,
    *,
    node: str,
    parent: str,
    label: str,
    branch: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return node, connector, arrowhead, and branch-label records for a top-down tree."""

    summary = process_tree_summary(
        data,
        node=node,
        parent=parent,
        label=label,
        branch=branch,
    )
    rows = data.to_dict(orient="records")
    row_by_node = {row[node]: row for row in rows}
    parent_by_node = {row[node]: _parent_value(row[parent]) for row in rows}
    children = {value: [] for value in row_by_node}
    for row in rows:
        parent_value = _parent_value(row[parent])
        if parent_value is not None:
            children[parent_value].append(row[node])

    leaves: list[Any] = []

    def collect_leaves(current: Any) -> None:
        child_nodes = children[current]
        if not child_nodes:
            leaves.append(current)
            return
        for child in child_nodes:
            collect_leaves(child)

    collect_leaves(summary.root)
    if len(leaves) == 1:
        leaf_x = {leaves[0]: 50.0}
    else:
        step = 84.0 / (len(leaves) - 1)
        leaf_x = {leaf: 8.0 + index * step for index, leaf in enumerate(leaves)}

    x_positions: dict[Any, float] = {}

    def assign_x(current: Any) -> float:
        child_nodes = children[current]
        if not child_nodes:
            x_positions[current] = leaf_x[current]
        else:
            child_positions = [assign_x(child) for child in child_nodes]
            x_positions[current] = sum(child_positions) / len(child_positions)
        return x_positions[current]

    assign_x(summary.root)
    depths = _depths(summary.root, children)
    if summary.max_depth == 0:
        y_positions = {summary.root: 50.0}
    else:
        step_y = 78.0 / summary.max_depth
        y_positions = {value: 10.0 + depth * step_y for value, depth in depths.items()}

    box_half_width = min(11.0, max(4.5, 32.0 / max(1, len(leaves))))
    box_half_height = min(5.0, max(3.2, 18.0 / max(1, summary.max_depth + 1)))

    node_records: list[dict[str, Any]] = []
    connector_records: list[dict[str, Any]] = []
    arrow_records: list[dict[str, Any]] = []
    branch_records: list[dict[str, Any]] = []

    for value, row in row_by_node.items():
        x = x_positions[value]
        y = y_positions[value]
        node_records.append(
            {
                "node_id": str(value),
                "label": str(row[label]),
                "x": x,
                "y": y,
                "x1": x - box_half_width,
                "x2": x + box_half_width,
                "y1": y - box_half_height,
                "y2": y + box_half_height,
                "depth": depths[value],
            }
        )

        parent_value = parent_by_node[value]
        if parent_value is None:
            continue

        parent_x = x_positions[parent_value]
        parent_bottom = y_positions[parent_value] + box_half_height
        child_top = y - box_half_height
        middle_y = (parent_bottom + child_top) / 2
        edge_id = f"{parent_value!s}->{value!s}"
        connector_records.extend(
            [
                {"edge_id": edge_id, "order": 0, "x": parent_x, "y": parent_bottom},
                {"edge_id": edge_id, "order": 1, "x": parent_x, "y": middle_y},
                {"edge_id": edge_id, "order": 2, "x": x, "y": middle_y},
                {"edge_id": edge_id, "order": 3, "x": x, "y": child_top},
            ]
        )
        arrow_records.append({"edge_id": edge_id, "x": x, "y": child_top})

        if branch:
            branch_value = row.get(branch)
            if not _is_missing(branch_value) and str(branch_value).strip():
                branch_records.append(
                    {
                        "edge_id": edge_id,
                        "label": str(branch_value),
                        "x": (parent_x + x) / 2,
                        "y": middle_y,
                    }
                )

    return node_records, connector_records, arrow_records, branch_records


def _assert_acyclic(parent_by_node: dict[Any, Any | None]) -> None:
    state: dict[Any, int] = {}

    def visit(current: Any) -> None:
        marker = state.get(current, 0)
        if marker == 1:
            raise ValueError("Process tree contains a cycle.")
        if marker == 2:
            return
        state[current] = 1
        parent = parent_by_node[current]
        if parent is not None:
            visit(parent)
        state[current] = 2

    for value in parent_by_node:
        visit(value)


def _depths(root: Any, children: dict[Any, list[Any]]) -> dict[Any, int]:
    depths = {root: 0}
    stack = [root]
    while stack:
        current = stack.pop()
        for child in reversed(children[current]):
            depths[child] = depths[current] + 1
            stack.append(child)
    return depths


def _parent_value(value: Any) -> Any | None:
    return None if _is_missing(value) else value


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False
