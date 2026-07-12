# HANDOFF

RESUME PACKET

- Goal: add first-class QQ, ECDF, and residual plots without introducing SciPy or widening into a general plotting library.
- Workflow State: statistical preparation helpers, intent-specific audits, renderers, tests, examples, docs, and a draft PR are being assembled on one feature branch.
- Branch: `agent/statistical-diagnostic-plots`
- Next task: run the full GitHub Actions suite, inspect generated Vega-Lite structures, and review the draft PR boundary.
- Verification: local pure-helper tests passed (`5 passed`); full repository CI is pending branch publication.
- Read first: `src/chart_contract/statistics.py`, `src/chart_contract/statistical_audit.py`, `src/chart_contract/chart.py`, `src/chart_contract/renderers/altair.py`, `tests/test_statistical_intents.py`, `artifacts/VERIFY.md`

## Current Repo State

- `Chart.qq()` compares sample quantiles with a deterministic normal reference and fitted reference line.
- `Chart.ecdf()` renders cumulative probability without histogram bin choices.
- `Chart.residual()` renders fitted-versus-residual points with a zero reference line.
- QQ and ECDF reuse the established distribution audit contract for numeric values, valid sample sizes, and grouped sample sizes.
- QQ adds explicit normal-reference and tie-density findings.
- Residual audits add fitted-value typing, complete-pair sample thresholds, residual-variation checks, and a zero-reference guarantee.
- Statistical preparation stays inside pandas and Python's standard library.

## Important Decisions

- Support only the normal QQ reference distribution in this slice; unsupported references fail audit and rendering explicitly.
- Prefer ECDF over adding more density estimators or smoothing parameters.
- Treat residual plots as deterministic diagnostic surfaces, not as proof of model adequacy.
- Keep `audit_spec()` generic; first-party statistical semantics live on the `Chart` intent audit path.

## Remaining Risks

- Grouped QQ plots can become visually busy with many groups; the existing color-category warning is the guardrail.
- QQ interpretation with discrete or heavily rounded values still requires human judgment.
- Statistical diagnostics do not replace hypothesis tests, calibration tests, or domain review.

## Next Recommended Task

Use CI, the generated spec structure, and the documented no-SciPy boundary as the final merge gate.
