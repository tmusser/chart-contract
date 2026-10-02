# HANDOFF

## Resume Packet

- Goal: make the amount of supplied evidence that actually survives into visible chart fields explicit before sharing.
- Branch: `agent/evidence-coverage-audit`.
- Base: `main` at `556e8f1df5bbbcf4b0d336b0d754383039f8bd33`.
- Pull request: #17 (`feat: audit evidence coverage and missingness`).
- Current slice: usable-row evidence coverage, grouped missingness imbalance, CLI trap, two new audit-profile rules, tests, and docs.
- Read first: `src/chart_contract/audit.py`, `tests/test_evidence_coverage.py`, `docs/EVIDENCE_COVERAGE.md`, and `docs/AUDIT_RULES.md`.

## Current Repo State

- Common first-party quantitative/statistical chart audits now emit `data.coverage.usable_rows` when required analytical fields are available.
- External spec audits compute coverage from visible analytical encoding channels rather than tooltip-only metadata.
- Usable-row coverage thresholds are:
  - 90%+ -> PASS
  - 50%-<90% -> WARN / REVIEW
  - below 50% -> FAIL / BLOCK
- The finding reports an inspectable receipt such as `8 / 10 rows (80.0%) complete across period, value`.
- If a required encoded field is absent, `data.encoding.fields` remains authoritative and coverage is skipped rather than fabricated.
- Grouped evidence emits `data.coverage.group_balance` when at least two groups each have at least five source rows.
- Eligible group coverage gaps below 20 percentage points PASS; gaps of 20 points or more WARN.
- Group labels are not copied into the portable finding message; only coverage range, group count, and grouping field are reported.
- The low-evidence CLI trap supplies ten rows but only four complete plotted rows and deterministically BLOCKs.
- The `audit-v0.2` profile now contains 57 rules, intentionally changing semantic profile identity.

## Important Decisions

- Evidence coverage is a complete-case visibility contract, not missing-data inference.
- A PASS does not prove retained rows are representative or missingness is random.
- A WARN/FAIL does not prove missingness caused bias; it says the visible chart is supported by materially less complete evidence than the source row count suggests.
- Group imbalance is a human-review signal, not a causal statement about group differences.
- Exactly 90% coverage PASSes; exactly 50% coverage WARNs rather than BLOCKs.
- Exactly a 20-percentage-point eligible-group gap WARNs.
- Groups below five source rows are excluded from the imbalance percentage to avoid tiny-denominator precision; their rows still affect overall coverage.
- Tooltip-only nulls do not reduce the main visible-evidence coverage.
- Null group labels reduce overall coverage because the visible grouping contract is incomplete, but null labels are excluded from per-group comparisons.
- Arbitrary transform-derived fields are not executed/reconstructed to manufacture coverage.
- Infinity and empty strings are not automatically classified as missing; that remains separate data/type-quality semantics.
- Older schema-0.4 reports correctly become stale-policy artifacts because the two new rules change `audit-profile-semantics-v1`.

## Verification

Initial CI run #213 exposed a floating-point edge at the exact 20-point grouped threshold.

The comparison was hardened with a tiny numeric tolerance, preserving the public threshold. GitHub Actions CI run #214 (`37053969737`) then passed on code-bearing head `8694d3a5b16d2f069ebdf5f186c05788eead8a55`:

- Python 3.10 -> PASSED
- Python 3.11 -> PASSED
- Python 3.12 -> PASSED
- Python 3.13 -> PASSED
- source compilation / environment checks -> PASSED
- CLI verdict + statistical diagnostic traps -> PASSED
- undeclared-transform CLI trap -> PASSED
- low-evidence-coverage CLI trap -> PASSED
- build/distribution inspection -> PASSED
- isolated wheel install / installed CLI and report-binding smoke -> PASSED

The final VERIFY/HANDOFF commits are documentation-only. Treat the final-head Actions run as the merge gate.

## Remaining Risks

- The thresholds are deterministic guardrails, not statistical missing-data theory.
- Coverage does not distinguish structural missingness from data-quality defects or intentionally inapplicable fields.
- The group-gap rule does not identify which group is low in the portable message.
- Coverage does not replay arbitrary transforms or infer the evidence population before upstream preprocessing.
- Very small groups are intentionally excluded from group-gap inference rather than assigned unstable percentages.

## Next Recommended Task

- Confirm final PR #17 CI remains green after these documentation-only commits.
- Review the public 90% / 50% / 20-point thresholds and merge if they match the desired contract.
- Keep imputation, missingness mechanism classification, and richer upstream population lineage as separate future PRs.
