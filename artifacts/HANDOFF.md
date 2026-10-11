# HANDOFF

## Resume Packet

- Goal: make source-row grain, duplicate/fanout keys, and source-to-display aggregation explicit and auditable.
- Branch: `agent/aggregation-grain-contract`.
- Base: `main` at `e088486eb3414567a2892af35c2307bc814156db`.
- Pull request: #23 (`feat: add aggregation grain contracts`).
- Current slice: first-party `grain_fields`, closed v1 grain receipts, chart/spec grain audits, encoding-level aggregate matching, join-fanout CLI trap, three new profile rules, tests, and docs.
- Read first: `src/chart_contract/grain.py`, `src/chart_contract/grain_audit.py`, `tests/test_grain_contract.py`, and `docs/GRAIN_CONTRACT.md`.

## Current Repo State

- `Chart.trend()`, `Chart.rank()`, and `Chart.compare()` accept optional `grain_fields`.
- Source-grain fields must exist, be non-null, and be unique across supplied rows.
- Duplicate declared grain keys fail `data.grain.unique`.
- If no grain is declared but repeated displayed-grain keys are supplied, `contract.grain.declared` warns.
- First-party descriptive charts do not aggregate.
- A finer unique source grain mapping many-to-one onto the displayed grain fails `contract.grain.aggregation` and first-party rendering refuses.
- First-party grain metadata, when valid, records source/output grain plus row/group receipts with `aggregation=null`.
- External specs can declare one encoding-level aggregate metric operation:
  - sum
  - mean
  - median
  - min
  - max
  - count
  - distinct
- External grain contracts record:
  - source grain fields
  - visible output grain fields
  - exact aggregate op/field or null
  - source row count
  - unique source-grain count
  - output group count
- Spec audits require exact output-grain parity, source-grain uniqueness, aggregate parity, and fresh counts.
- Encoding aggregates remain transform-inventoried, transform-declared, and lineage-bound independently of grain metadata.
- Binned histogram aggregation is excluded from this business-grain rule.
- `examples/traps/join_fanout_grain.*` demonstrates valid sum/transform metadata that still blocks because account-month source grain is duplicated.
- The `audit-v0.2` profile now contains 75 rules.

## Important Decisions

- Grain is row identity, not a deduplication hint.
- Duplicate grain keys are not automatically collapsed.
- First-party chart-contract does not become an aggregation engine; users aggregate upstream deliberately and then pass one row per displayed grain.
- Repeated displayed keys without declared grain are REVIEW, not immediate BLOCK, because v1 cannot know whether repeated observations are legitimate finer-grain evidence.
- Once grain is declared, hidden many-to-one collapse without aggregation is a deterministic failure.
- External v1 aggregation support is deliberately bounded to one encoding-level metric aggregate.
- Matching grain metadata is structural consistency only; it does not prove the business key, join logic, or reducer choice is analytically correct.
- Histogram bin/count transforms are distribution mechanics, not business-grain collapse.
- Older schema-0.4 reports become stale-policy artifacts because three new grain rules change profile semantic identity.

## Verification

GitHub Actions CI run #247 (`38097803031`) passed on code-bearing head `e1b8a8ce5d728ba0c2f3ded4871d21920c12d264`:

- Python 3.10 -> PASSED
- Python 3.11 -> PASSED
- Python 3.12 -> PASSED
- Python 3.13 -> PASSED
- source compilation / environment checks -> PASSED
- all prior CLI trap paths -> PASSED
- `join_fanout_grain` installed-CLI trap -> PASSED
- build/distribution inspection -> PASSED
- isolated wheel install / installed CLI and report-binding smoke -> PASSED

The final VERIFY/HANDOFF commits are documentation-only. Treat the final-head Actions run as the merge gate.

## Remaining Risks

- V1 does not support explicit transform-array aggregate reconstruction or more than one aggregate metric.
- A user can declare the wrong but unique business key; uniqueness is not semantic truth.
- The contract cannot detect fanout that happened upstream and was already collapsed before supplied evidence.
- Aggregate suitability remains human judgment.
- First-party callers who want aggregated charts must aggregate upstream and declare the resulting grain rather than asking chart-contract to do it.

## Next Recommended Task

- Confirm final PR #23 CI remains green after VERIFY/HANDOFF.
- Merge if the first-party no-auto-aggregation boundary and external single-aggregate v1 are desired.
- Keep multi-metric aggregation plans, composite reducer pipelines, and upstream join lineage as separate future work.
