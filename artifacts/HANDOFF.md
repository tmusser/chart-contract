# HANDOFF

## Resume Packet

- Goal: make calendar/rolling exposure windows explicit and auditable for temporal baseline comparisons.
- Branch: `agent/time-window-comparability`.
- Base: `main` at `ca2c7fd7d56409753859035010d2b16795ab015c`.
- Pull request: #22 (`feat: audit time-window comparability`).
- Current slice: first-party window API fields, closed v1 period receipts, chart/spec audits, full-month-vs-MTD CLI trap, three new profile rules, tests, and docs.
- Read first: `src/chart_contract/time_window.py`, `src/chart_contract/time_window_audit.py`, `tests/test_time_window_contract.py`, and `docs/TIME_WINDOW_CONTRACT.md`.

## Current Repo State

- `Chart.trend()` and `Chart.compare()` comparison contracts may additionally declare:
  - `window_kind`
  - `window_granularity`
  - `baseline_start`
  - `baseline_end`
  - `target_start`
  - `target_end`
  - `baseline_complete`
  - `target_complete`
- `window_kind` supports `calendar` and `rolling`.
- Calendar granularities are day/week/month/quarter/year.
- Rolling windows require `window_granularity=None`.
- Complete calendar periods are structurally validated against their declared granularity.
- Date-like baseline comparisons with no time-window contract produce REVIEW.
- Complete-vs-incomplete exposure blocks.
- Two incomplete windows produce REVIEW.
- Rolling windows must have equal inclusive-day duration.
- Unequal complete calendar periods produce REVIEW rather than BLOCK.
- No prorating or normalization is performed.
- First-party specs stamp inclusive baseline/target day counts as durable receipts.
- Spec audits recompute those day counts and block stale receipt metadata.
- Time-window metadata requires an explicit comparison contract.
- `examples/traps/full_month_vs_mtd.*` demonstrates valid comparison arithmetic that blocks because September is complete while October covers only days 1-6.
- The `audit-v0.2` profile now contains 72 rules.

## Important Decisions

- Window semantics are never inferred from labels such as “September,” “MTD,” or “last 28 days.”
- Complete calendar periods may legitimately differ in duration, so unequal calendar day counts warn.
- Rolling windows are defined by exposure duration, so unequal durations block.
- Completeness state is part of the explicit contract but is not upstream-ingestion attestation.
- No automatic prorating or normalization.
- Calendar week v1 means a complete seven-day span; locale-specific week anchors are deferred.
- The contract does not determine whether totals, averages, or rates are exposure-sensitive enough to require normalization.
- Existing comparison arithmetic remains separate: a numerically correct +20 can still block because its periods are structurally incomparable.
- Older schema-0.4 reports become stale-policy artifacts because three new time-window rules change profile semantic identity.

## Verification

Initial CI run #243 failed because three existing comparison-contract tests used year-like selectors (`2025`, `2026`) and still expected READY with no explicit exposure windows.

Those fixtures were upgraded to complete 2025/2026 calendar-year contracts rather than weakening temporal detection.

GitHub Actions CI run #244 (`37797073709`) then passed on code-bearing head `ad2d51f209207efae40c501b5bcc06f8f56e5738`:

- Python 3.10 -> PASSED
- Python 3.11 -> PASSED
- Python 3.12 -> PASSED
- Python 3.13 -> PASSED
- source compilation / environment checks -> PASSED
- all prior CLI trap paths -> PASSED
- `full_month_vs_mtd` installed-CLI trap -> PASSED
- build/distribution inspection -> PASSED
- isolated wheel install / installed CLI and report-binding smoke -> PASSED

The final VERIFY/HANDOFF commits are documentation-only. Treat the final-head Actions run as the merge gate.

## Remaining Risks

- Completeness flags can be incorrect if upstream producers misdeclare ingestion state.
- Business calendars and holiday exposure are not modeled.
- Calendar duration warnings are intentionally metric-agnostic.
- The v1 schema compares one baseline window to one target window; recurring/multi-period window families are not represented.
- Time zones and sub-day windows are out of scope; dates are day-level ISO boundaries.

## Next Recommended Task

- Confirm final PR #22 CI remains green after VERIFY/HANDOFF.
- Merge if the current REVIEW/BLOCK boundaries match the intended policy.
- Keep business-day exposure, time-zone/sub-day windows, and automatic exposure adjustment out of this slice.
