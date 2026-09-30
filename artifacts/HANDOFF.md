# HANDOFF

## Resume Packet

- Goal: make percent-valued chart representation explicit without guessing scale from observed values or silently rescaling data.
- Branch: `agent/percent-representation-contract`.
- Base: `main` at `0ef60fb788c5ad4a24878c06905424e65a15be61`.
- Pull request: #15 (`feat: make percent value representation explicit`).
- Current slice: public `value_representation` contract, percent rendering semantics, external-spec audits, two new audit-profile rules, tests, and docs.
- Read first: `src/chart_contract/audit.py`, `src/chart_contract/chart.py`, `src/chart_contract/contracts.py`, `src/chart_contract/renderers/altair.py`, `tests/test_percent_semantics.py`, and `docs/PERCENT_SEMANTICS.md`.

## Current Repo State

- Quantitative first-party chart constructors accept optional `value_representation`.
- Explicit percent units are `percent`, `percentage`, and `%`.
- Supported raw representations are `fraction` and `percentage_points`.
- Missing representation on explicit percent presentation yields `labels.percent.representation: WARN`.
- Unsupported, malformed, or representation-without-percent declarations yield `FAIL`.
- First-party fractional percent charts use Vega-Lite percent axis/tooltip formatting; source DataFrames are not rescaled or mutated.
- Percentage-point charts remain on their raw numeric scale and avoid Vega-Lite's fraction-scaling percent formatter.
- External spec audits can recover representation from `usermeta.value_representation`.
- `labels.percent.format` warns when fractional values lack percent formatting and blocks percentage-point values passed through a percent formatter.
- Generic `rate` units are deliberately not inferred as percentages.
- The `audit-v0.2` profile now contains 53 rules, so this PR intentionally changes audit-profile semantic identity.

## Important Decisions

- Never infer representation from value ranges. `0.42` and `42` remain author-declared semantics.
- Never multiply or divide chart data merely to satisfy or render the percent contract.
- `value_representation` is not a generic scaling API; using it without explicit percent presentation semantics blocks.
- Percent representation metadata describes presentation scale only. It does not validate metric construction, denominators, statistical meaning, or source truth.
- A generic rate may represent events/time, events/person, ratios, indices, or other units and remains outside this percent-specific slice.
- Older schema-0.4 reports correctly become stale-policy artifacts because adding these rules changes `audit-profile-semantics-v1`.

## Verification

GitHub Actions CI run #205 (`36785086891`) passed on the code-bearing head:

- Python 3.10 -> PASSED
- Python 3.11 -> PASSED
- Python 3.12 -> PASSED
- Python 3.13 -> PASSED
- CLI verdict and statistical diagnostic traps -> PASSED
- build/distribution inspection -> PASSED
- isolated wheel install / installed CLI smoke -> PASSED

The final VERIFY/HANDOFF commits are documentation-only. Treat the final-head Actions run as the merge gate.

## Remaining Risks

- External Vega-Lite specs using arbitrary expression-based formatting may sit outside the deterministic format check.
- Percent representation does not prove that upstream values use the declared convention truthfully.
- The name `percentage_points` is an explicit scale declaration; downstream interpretation of changes still requires domain/statistical judgment.
- Broader rate denominator semantics remain intentionally unsolved.

## Next Recommended Task

- Confirm final PR #15 CI remains green after these documentation-only commits.
- Review the public naming and severity boundaries, then merge if they match the desired contract.
- Keep broader rate/ratio semantics or transform-lineage work as separate PRs.
