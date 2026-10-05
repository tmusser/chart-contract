# HANDOFF

## Resume Packet

- Goal: make rank ordering, duplicate categories, top-N truncation, cutoff ties, and omitted-category evidence explicitly auditable.
- Branch: `agent/rank-topn-contract`.
- Base: `main` at `9e9ec644fbe60ca941e8712de7b41e98ce497944`.
- Pull request: #19 (`feat: harden rank and top-N contracts`).
- Current slice: `top_n` API, deterministic rank selection, chart/spec rank audits, full-source top-N filtering, five new profile rules, CLI trap, tests, docs, and refreshed hero proof spec.
- Read first: `src/chart_contract/rank.py`, `src/chart_contract/rank_audit.py`, `src/chart_contract/renderers/altair.py`, `tests/test_rank_contract.py`, and `docs/RANK_CONTRACT.md`.

## Current Repo State

- `Chart.rank()` accepts optional `top_n`.
- `top_n=None` means the full eligible category set; positive integers request explicit truncation.
- Duplicate non-null categories fail `data.rank.category_unique`; rank code never silently aggregates duplicates.
- Rank ordering is metric-descending with category identity used only as deterministic display order among exact metric ties.
- Numeric ranking compares original values rather than coercing to float.
- Top-N uses `include_cutoff_ties`; exact ties crossing the cutoff are all displayed and produce `data.rank.cutoff_tie=WARN`.
- First-party rank specs carry `chart_contract_intent="rank"` and a closed v1 `rank_contract`.
- Rank contract metadata declares category/metric fields, order, top_n, tie policy, eligible/displayed/omitted counts, and whether cutoff ties expanded the view.
- Eligible categories require non-null category + metric; incomplete rows remain visible to evidence-coverage auditing.
- First-party top-N rendering preserves full source rows and applies one category `oneOf` filter for the displayed set.
- Top-N filters are also covered by `transform.declaration` and `transform.lineage.receipts`.
- Opt-in rank spec audits reproduce the expected rank contract and selected set from supplied full evidence.
- Exact visual category sort is audited, so a bar reorder blocks even when values are unchanged.
- `examples/traps/wrong_rank_topn_filter.*` proves a transform-consistent but analytically wrong selected category set blocks through the rank contract.
- The `audit-v0.2` profile now contains 63 rules.

## Important Decisions

- One row per category is a hard contract; aggregation policy must be explicit upstream.
- `top_n` is truncation intent, not inferred from displayed row count.
- Cutoff ties are never silently split; all exact ties are included.
- Category ordering inside exact metric ties is presentation stabilization only and does not create distinct analytical ranks.
- First-party specs retain full source evidence specifically so omitted-category counts and selected sets remain re-auditable.
- Rank omissions count only eligible categories, not rows missing category/metric values.
- External specs must explicitly opt into rank semantics with `usermeta.chart_contract_intent="rank"`.
- The supported top-N filter is intentionally bounded to one category `oneOf` predicate; generic transform execution remains out of scope.
- A passing rank contract does not prove top-N is the right presentation or that an externally supplied source population is complete.
- Older schema-0.4 reports correctly become stale-policy artifacts because five new rank rules change profile semantic identity.

## Verification

Initial CI run #222 failed only because an existing regression still expected `sort="-x"`.

The new renderer intentionally emits the exact deterministic category order, so the regression was updated to assert that stronger contract. GitHub Actions CI run #223 (`37379008106`) then passed on code-bearing head `f4110be16eda85b6ac94d0aeda80e86f5e8fba46`:

- Python 3.10 -> PASSED
- Python 3.11 -> PASSED
- Python 3.12 -> PASSED
- Python 3.13 -> PASSED
- source compilation / environment checks -> PASSED
- all CLI trap paths, including `wrong_rank_topn_filter` -> PASSED
- build/distribution inspection -> PASSED
- isolated wheel install / installed CLI and report-binding smoke -> PASSED

The final VERIFY/HANDOFF/proof-artifact commits are documentation/data-only. Treat the final-head Actions run as the merge gate.

## Remaining Risks

- First-party full-source preservation makes top-N auditable but can increase emitted spec size for very large rank datasets.
- The v1 contract has one fixed descending order and one tie policy; user-defined analytical secondary tiebreakers are not yet modeled.
- The rank-specific filter reconstruction supports the first-party bounded `oneOf` shape only.
- External rank metadata can still lie about evidence not supplied to the audit; the contract verifies the supplied evidence, not remote source completeness.
- Very long tie groups can intentionally make a top-N chart display materially more than N categories.

## Next Recommended Task

- Confirm final PR #19 CI remains green after the verification/handoff/proof-artifact commits.
- Merge if the explicit v1 rank contract and tie-inclusive top-N behavior match the intended policy.
- Consider user-declared secondary tiebreak semantics only as a separate future contract rather than weakening the current no-hidden-tiebreak rule.
