# HANDOFF

## Resume Packet

- Goal: bind each auditable Vega-Lite transform occurrence to exact structural identity plus bounded field lineage.
- Branch: `agent/transform-lineage-receipts`.
- Base: `main` at `0a76d4c53c4f1d6206d5415d28bb1484eff9a464`.
- Pull request: #18 (`feat: add transform lineage receipts`).
- Current slice: public receipt builder, exact spec-audit receipt parity, first-party renderer stamping, stale-receipt CLI trap, one new profile rule, tests, and docs.
- Read first: `src/chart_contract/transforms.py`, `src/chart_contract/spec_policy.py`, `tests/test_transform_lineage.py`, `docs/TRANSFORM_LINEAGE.md`, and `docs/TRANSFORM_CONTRACT.md`.

## Current Repo State

- `build_transform_lineage(spec)` returns `{"version": 1, "receipts": [...]}`.
- Each receipt contains exactly:
  - `kind`
  - `location`
  - `operation_sha256`
  - sorted unique `input_fields`
  - sorted unique `output_fields`
- Explicit transform-array digests cover the complete canonical transform object.
- Encoding-level aggregate/bin/stack/timeUnit receipts hash a bounded payload containing field + operator configuration.
- JSON key-order changes do not change receipt digests.
- `transform.lineage.receipts` blocks missing, malformed, changed, missing-location, and stale receipts.
- A no-transform spec passes without lineage; stale non-empty lineage on a no-transform spec blocks.
- First-party renderers compute receipts after Altair has emitted the final Vega-Lite structure.
- Histograms preserve encoding-level aggregate/bin receipts.
- Violins preserve density receipts; ungrouped Altair violins may expose the renderer-generated `_distribution` grouping field in lineage.
- `examples/traps/stale_transform_lineage.*` demonstrates a same-kind filter edit that passes kind declaration but fails occurrence receipt parity.
- The `audit-v0.2` profile now contains 58 rules.

## Important Decisions

- Receipt identity is separate from transform-kind declaration and full report/spec input binding.
- Same-kind transform edits must invalidate receipts.
- Receipts bind actual emitted structure; renderer-generated fields are not sanitized away merely to make lineage prettier.
- Field lineage is bounded and structural, not an arbitrary expression evaluator.
- Calculate-expression parsing recognizes direct `datum.field` and bracket references only.
- A matching receipt is not proof of transform execution, correctness, user intent, scientific validity, or upstream provenance.
- Do not hand-edit receipt hashes; regenerate from the final spec.
- First-party stamping occurs after rendering so metadata reflects emitted Vega-Lite rather than an approximation of intended transforms.
- Upstream SQL/dbt/Python lineage remains out of scope.
- Older schema-0.4 reports correctly become stale-policy artifacts because adding `transform.lineage.receipts` changes profile semantic identity.

## Verification

Initial CI run #217 failed because one test expected an ungrouped violin density receipt to list only the source metric, while Altair also emits an internal `_distribution` grouping field.

The test was corrected to preserve actual emitted structure. GitHub Actions CI run #218 (`37160779607`) then passed on code-bearing head `eaf70a7f74917c3f0f8f408b7678deeb4f3a85bc`:

- Python 3.10 -> PASSED
- Python 3.11 -> PASSED
- Python 3.12 -> PASSED
- Python 3.13 -> PASSED
- source compilation / environment checks -> PASSED
- all CLI trap paths, including stale-transform-lineage -> PASSED
- build/distribution inspection -> PASSED
- isolated wheel install / installed CLI and report-binding smoke -> PASSED

The final VERIFY/HANDOFF commits are documentation-only. Treat the final-head Actions run as the merge gate.

## Remaining Risks

- Structural hashes are not signatures, execution evidence, or remote attestation.
- Bounded field extraction may omit semantically referenced fields hidden inside unsupported expression patterns.
- Renderer-generated intermediate fields may appear in first-party receipts.
- Receipt version 1 intentionally does not model upstream transformation systems, dataset versions, or cross-artifact DAGs.
- A malicious writer can recompute consistent receipts after changing a spec; the receipt is deterministic drift detection, not tamper-proof authorship.

## Next Recommended Task

- Confirm final PR #18 CI remains green after these documentation-only commits.
- Review and merge if the v1 receipt schema and structural-field-lineage boundary are desirable.
- Keep transform replay/execution and upstream lineage DAG integration as separate future PRs.
