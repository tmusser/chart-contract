# HANDOFF

RESUME PACKET

- Goal: close deterministic audit blind spots without adding chart intents or widening product scope.
- Workflow State: runtime fixes, regression tests, audit-rule docs, changelog, and verification evidence are prepared for a draft PR.
- Branch: `agent/close-audit-blind-spots`
- Next task: inspect GitHub Actions, update `artifacts/VERIFY.md` with the full-suite result, and review the PR diff.
- Verification: targeted regression suite (`16 passed`), 2,000 malformed/spec-shape probes without exceptions, and Python bytecode compilation.
- Read first: `src/chart_contract/audit.py`, `src/chart_contract/contracts.py`, `src/chart_contract/renderers/altair.py`, `tests/test_hidden_regressions.py`, `artifacts/VERIFY.md`

## Current Repo State

- Spec audits validate encoded-field presence and quantitative dtypes for object and shorthand Vega-Lite encodings.
- Trend completeness uses non-null x/y pairs for both chart and simple/layered line-spec audits.
- Distribution thresholds use non-null numeric metric observations and valid per-group rows.
- Generated Vega-Lite specs retain source, unit, caveat, filters, and custom metadata in top-level `usermeta`.
- Numeric trend x fields render as quantitative axes.
- Unsupported direct chart intents produce `visual.intent.match` FAIL instead of an audit PASS followed by a renderer exception.
- Decoration detection is token-aware and ignores data payloads, dataset hashes, and provenance values.

## Important Decisions

- Preserve the v0.1 and v0.3-preview intent boundaries; this is a correctness-only change.
- Prefer deterministic failures for invalid data contracts over permissive READY verdicts.
- Audit the first supported analytical layer in layered specs rather than pretending arbitrary composition is fully understood.
- Preserve metadata at render time so chart-to-spec round trips do not lose audit evidence.

## Remaining Risks

- Complex layered/concatenated/faceted Vega-Lite specs remain only partially inspected.
- Visual browser rendering is not part of the deterministic gate.

## Next Recommended Task

Use the draft PR's CI result and changed-file review as the final merge gate.
