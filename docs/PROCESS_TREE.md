# Process Tree Contract

Use `Chart.process_tree()` for a rooted decision tree or process map: one entry point, directed parent-child steps, optional labeled branches, and no cycles.

This intent is deliberately **not** a treemap. Node area, spacing, and box size do not encode magnitude.

## Evidence shape

Provide one row per process node.

| Field | Meaning |
| --- | --- |
| `node` | Column containing the unique node identifier. |
| `parent` | Column containing the parent node identifier; empty only for the single root. |
| `label` | Human-readable text rendered inside the node. |
| `branch` | Optional text attached to the incoming edge, such as `Yes`, `No`, or `Needs review`. |

Example:

```text
step_id   parent_id   step                branch
start     <null>      Request received
review    start       Review request
approve   review      Approve             Yes
revise    review      Revise              No
ship      approve     Ship
```

The branch value belongs to the **child row**, because it labels the edge from that row's parent into the child.

## Python API

```python
import pandas as pd
from chart_contract import Chart

frame = pd.DataFrame(
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

chart = Chart.process_tree(
    data=frame,
    node="step_id",
    parent="parent_id",
    label="step",
    branch="branch",
    claim="Requests move from intake through review to revision or approval.",
    source="workflow.request_approval",
    title="Request approval flow",
)

report = chart.audit()
spec = chart.to_vega_lite()
```

## Structural contract

A shareable process tree must have:

- one non-null, unique node ID per row;
- exactly one root with an empty parent;
- every non-root parent reference resolving to an existing node;
- a non-empty display label for every node;
- no parent cycle;
- every node reachable from the single root.

The first-party layout is deterministic:

- root at the top;
- depth increases downward;
- sibling order follows input row order;
- parent-child links use elbow connectors and directional arrowheads;
- optional branch labels sit on their incoming edges.

## What geometry means

The geometry is schematic.

- Box size does not encode importance, duration, probability, volume, or cost.
- Horizontal spacing does not encode distance or similarity.
- Vertical spacing indicates tree depth only.
- Branch labels are authoritative text when supplied.
- Parent-child topology is authoritative for the declared process structure.

The generated Vega-Lite artifact records the structural contract under `usermeta.process_tree`, including the column roles, root ID, node count, edge count, maximum depth, and layout convention.

## Audit rules

`Chart.process_tree().audit()` applies deterministic checks including:

- `data.process_tree.columns`
- `data.process_tree.node_unique`
- `data.process_tree.labels`
- `data.process_tree.root`
- `data.process_tree.parent_reference`
- `data.process_tree.acyclic`
- `visual.process_tree.structure`

The ordinary claim, source, title, filter-scope, causal-language, and decoration checks also apply.

## Boundaries

This intent is intentionally a **rooted tree**, not a general flowchart engine or graph library.

It does not support:

- loops or retry edges;
- nodes with multiple parents;
- cross-links between branches;
- swimlanes;
- arbitrary DAG layout;
- automatic inference of a process from prose.

If the real workflow is cyclic or has cross-links, representing it as a tree would lose information; use a graph/flowchart tool rather than forcing it through this intent.

Passing the structural audit means the declared rows form a valid rooted tree. It does not prove that the documented process is complete, current, efficient, or operationally correct.
