# HANDOFF

RESUME PACKET

- Goal: harden QQ and residual diagnostics with claim-support traps, reference-line contracts, and agent-facing claim guidance.
- Workflow State: runtime rules, first-party spec semantics, four trap triplets, tests, docs, and CI are published in draft PR #5; the full permanent GitHub Actions suite passed.
- Branch: `agent/diagnostic-claim-traps`
- Pull request: #5 (`feat: harden diagnostic claim audits`)
- Next task: review the deterministic thresholds and trap verdicts, then squash-merge if the boundaries are acceptable.
- Verification: full pytest, all legacy CLI smoke checks, and all four diagnostic trap checks passed in GitHub Actions run #155.
- Read first: `src/chart_contract/statistical_audit.py`, `src/chart_contract/audit.py`, `src/chart_contract/renderers/altair.py`, `tests/test_statistical_intents.py`, `docs/DIAGNOSTIC_CLAIMS.md`, `artifacts/VERIFY.md`

## Current Repo State

- First-party QQ specs declare `chart_contract_intent=qq` and `qq_reference_distribution=normal`; residual and ECDF specs preserve their statistical intent without changing metadata for older chart types.
- QQ audits require a fitted normal reference line and warn when outer-tail departure reaches 0.8 sample standard deviations.
- Residual audits warn when absolute fitted/residual correlation reaches 0.5 or ordered-thirds mean shift reaches one residual standard deviation.
- Nonnumeric fitted values fail deterministically without entering the pattern calculation.
- `audit_spec()` applies these semantics only when first-party statistical intent metadata is declared.
- Trap fixtures distinguish complete-but-overstated diagnostics (`REVIEW`) from structurally invalid or undersampled diagnostics (`BLOCK`).

## Important Decisions

- Treat reference lines as visual evidence contracts, not optional decoration.
- Keep obvious-pattern detection deterministic and explainable rather than adding opaque tests or smoothing.
- Use `REVIEW` for claims contradicted by visible tail/pattern evidence; reserve `BLOCK` for missing reference layers, invalid fields, or fewer than five complete observations.
- Preserve the existing `usermeta` contract for trend, rank, compare, histogram, boxplot, and violin charts.
- Keep normality and model-adequacy language explicitly non-certifying.

## Remaining Risks

- The thresholds catch obvious tail, monotonic, and broad curved structure; they do not exhaust every residual failure mode such as heteroskedasticity or autocorrelation.
- QQ tail checks use a fitted normal location-scale line and are intentionally not a formal normality test.
- First-party spec semantics depend on `usermeta.chart_contract_intent`; arbitrary external specs remain under the generic audit contract.
- The branch history is noisy from connector-assisted publication, so squash merge is recommended.

## Next Recommended Task

Review draft PR #5 with special attention to the 0.8-SD QQ threshold, the residual correlation/thirds thresholds, and the REVIEW-versus-BLOCK trap split.
