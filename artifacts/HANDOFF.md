# HANDOFF

## Resume Packet

- Goal: add a first-class rooted decision/process-tree diagram without broadening chart-contract into a general graph library.
- Branch: `agent/add-process-tree`.
- Base: `main` at `6e179e2eaa70256c41e05580669964353543afc0`.
- Current slice: `Chart.process_tree()`, structural validation, deterministic top-down flowchart layout, audit-profile rules, example, tests, and docs.
- Read first: `src/chart_contract/process_tree.py`, `src/chart_contract/process_tree_audit.py`, `src/chart_contract/chart.py`, `src/chart_contract/renderers/altair.py`, `tests/test_process_tree.py`, and `docs/PROCESS_TREE.md`.

## Current Repo State

- `Chart.process_tree()` takes one row per node and column names for `node`, `parent`, `label`, and optional `branch`.
- Exactly one row must have an empty parent. Every other parent must resolve to an existing node.
- Node IDs must be non-null and unique; labels must be non-empty; parent relationships must be acyclic.
- The layout is deterministic and top-down. Sibling order follows input row order.
- The renderer uses elbow connectors, directional arrowheads, boxed nodes, node labels, and optional branch text.
- The generated Vega-Lite artifact records `usermeta.chart_contract_intent=process_tree` and a `usermeta.process_tree` structural summary.
- The machine-readable `audit-v0.2` profile and `docs/AUDIT_RULES.md` now contain 51 rules.

## Important Decisions

- Public API name is `process_tree`, not `decision_tree`, to avoid implying an ML classifier.
- This is a rooted-tree intent, not arbitrary graph layout.
- Parent-child topology, direction, node labels, and optional branch text are authoritative.
- Box size and spacing are schematic and do not encode probability, duration, importance, volume, or causal strength.
- Branch text belongs to the child row and labels the incoming edge from its parent.
- Cycles, multi-parent nodes, cross-links, DAGs, and swimlanes are intentionally out of scope.
- No new runtime dependency or external layout engine is introduced.

## Verification

Focused tests cover:
- structural summary and deterministic layout;
- renderer layers and usermeta;
- READY valid tree;
- BLOCK duplicate IDs, unknown parents, multiple roots, and cycles;
- refusal to render invalid structures;
- example-script execution;
- 51-rule profile/documentation parity.

A local clone/render attempt could not run because this environment cannot resolve github.com. GitHub Actions is therefore the authoritative executable gate; do not claim browser-level visual inspection.

## Remaining Risks

- Very wide trees or long labels can become crowded in a static Vega-Lite canvas.
- The renderer does not automatically wrap arbitrary labels.
- Generic `audit_spec()` does not reconstruct process-tree topology from layered Vega-Lite output; use `Chart.process_tree().audit()` before rendering.
- A structurally valid tree can still document a process that is incomplete, stale, or operationally wrong.

## Next Recommended Task

- Open the PR and let CI validate Altair/Vega-Lite schema compatibility across Python 3.10-3.13.
- If green, inspect the final diff for accidental broadening into general graph semantics.
- Keep any future DAG/loop/swimlane work as a separate intent or separate tool rather than weakening the rooted-tree contract.
