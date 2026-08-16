# HANDOFF

## Resume Packet

- Goal: prevent AI-generated chart specs from silently changing quantitative scale or normalization defaults without an explicit user request.
- Workflow state: draft PR #8 is open; implementation, focused tests, agent guidance, SPEC updates, and visual-default documentation are committed. CI run #179 is queued.
- Branch: `agent/require-scale-normalization-opt-in`
- Base: `main` at `1be9e17bd7dd9e5d7174b8a9232e58191fab8bf1`.
- Next task: inspect CI #179. If it fails, fix only the scale/normalization policy slice; if it passes, perform one final PR diff review before deciding whether to mark ready.
- Read first: `src/chart_contract/spec_policy.py`, `tests/test_spec_policy.py`, `tests/test_cli_visual_defaults.py`, `docs/VISUAL_DEFAULTS.md`, and `docs/AUDIT_RULES.md`.

## Current Repo State

- Existing spec audits already block `scale.zero=false` on quantitative bar axes through `scale.bar.nonzero_baseline`.
- This branch wraps the existing `audit_spec()` rather than rewriting the mature audit implementation.
- Public Python audits and the CLI both route through the new wrapper.
- `scale.override.authorization` blocks explicit quantitative x/y scale changes unless `usermeta.user_requested_scale_override=true` is declared.
- `scale.normalization.authorization` blocks native Vega-Lite stack normalization unless `usermeta.user_requested_normalization=true` is declared.
- `scale.bar.explicit_domain_zero` additionally blocks numeric bar domains that explicitly exclude zero even if a scale override was user-requested.
- Untouched scale defaults require no authorization metadata.

## Important Decisions

- User-request metadata is a declaration boundary, not proof that the user actually requested the transformation.
- Agents must not add authorization metadata merely to obtain a passing audit.
- Requested zoom/cropping on line or point charts may pass the new policy because positional comparison can legitimately use a requested local domain.
- Truncated quantitative bars remain blocked because bar length depends on the baseline.
- Native `stack="normalize"` and stack transforms with `offset="normalize"` are covered; arbitrary pre-normalized data and semantic normalization hidden in custom calculations remain outside deterministic audit scope.
- No new renderer, chart intent, runtime dependency, or automatic chart correction was added.

## Verification

- Focused coverage: `tests/test_spec_policy.py`.
- CLI routing coverage: `tests/test_cli_visual_defaults.py`.
- Local execution was unavailable because the execution container could not resolve GitHub, so no local pytest result should be claimed.
- GitHub Actions CI run #179 is the executable validation gate for the current head.

## Remaining Risks

- The audit trusts the truthfulness of `usermeta.user_requested_*` declarations.
- Dynamic `domainRaw` expressions are treated as scale overrides for authorization but are not fully analyzed for whether zero is present on bar axes.
- Arbitrary calculate/window/preprocessing steps can normalize values before the spec reaches the audit and are not reconstructable from generic Vega-Lite semantics.
- The new policy adds two PASS findings to ordinary public/CLI spec audits, so tests that assert exact finding counts may need adjustment if any exist outside the focused suite.

## Next Recommended Task

Wait for CI #179, then inspect any failures for exact-count/report-shape assumptions before changing policy semantics. If CI is green, review the diff for scope creep and mark PR #8 ready only if the metadata boundary and bar exception still read cleanly.
