# Changelog

## [Unreleased]

### Added

- Deterministic SHA-256 input bindings for public spec audits and first-party chart audit reports, covering the audited subject, explicit data, claim, and installed package version.
- Bound report schema `0.3` with component hashes, a bundle hash, and `matches_spec(...)` / `matches_chart(...)` verification helpers.
- Audit provenance documentation describing content identity, reproducibility, and the boundary between matching inputs and analytical validity.
- Deterministic spec-audit policy that blocks undeclared quantitative scale overrides and native Vega-Lite normalization.
- Explicit `usermeta.user_requested_scale_override` and `usermeta.user_requested_normalization` declarations for genuinely user-requested visual transformations.
- Dedicated visual-default policy tests and documentation, including the rule that truncated quantitative bars remain blocked even with a user-request declaration.
- First-class `Chart.set_membership()` support for audited two-set membership and Venn-style relationship charts.
- Row-level set evidence checks for required columns, binary membership, unique members, and reconciled A-only/overlap/B-only/neither counts.
- Schematic layouts for partial overlap, disjoint, subset, and equal-set relationships, with authoritative region labels preserved in Vega-Lite metadata.
- A runnable `examples/set_membership.py` artifact and dedicated set-membership contract guidance.
- A checked-in Vega-Lite proof artifact for the set-membership example.
- A package-build CI job that builds both distributions, checks metadata, installs the wheel in isolation, and smoke-tests the installed CLI and JSON report shape.
- CI coverage across the complete supported Python 3.10-3.13 range.

### Changed

- Public `audit_spec()` and `Chart.audit()` results are now content-bound so a report can be checked against the inputs being shared instead of surviving silent post-audit mutations.
- Public `audit_spec()` and the CLI audit gate now apply the visual-default consent policy after the existing deterministic spec audit.
- Hardened CI with read-only permissions, disabled checkout credentials, pip caching, concurrency cancellation, job timeouts, dependency checks, and source compilation.
- Preserved the chart-specific verdict and statistical-diagnostic trap checks across every supported Python version.
- Made pytest fail closed on unknown configuration, undeclared markers, and unexpected `xfail` passes.
- Restored the README's diagnostic trap outcomes, companion-artifact explanation, and suite navigation after the set-membership insertion.
- Refreshed the roadmap and workflow artifacts to distinguish released v0.2.0 behavior from the unreleased set-membership slice.

## [0.2.0] - 2026-07-12

### Added

- CLI audit gate for Vega-Lite specs from disk via `chart-contract audit spec`.
- Optional CSV and JSON data input for CLI audits.
- Text, JSON, and Markdown report output from the same audit result.
- CI-friendly exit behavior for `READY`, `REVIEW`, and `BLOCK`.
- Runnable trap fixtures under `examples/traps/` for weak claims, missing provenance, pie/arc failures, severe QQ tail departure (`REVIEW`), missing QQ reference lines (`BLOCK`), obvious residual structure (`REVIEW`), and tiny diagnostic samples (`BLOCK`).
- First-class `Chart.qq()`, `Chart.ecdf()`, and `Chart.residual()` statistical diagnostic intents.
- Deterministic normal-reference QQ quantiles and empirical-CDF preparation without adding SciPy or external data dependencies.
- Statistical audit rules for QQ reference support, tie density, fitted-value types, residual sample size, and residual variation.
- A runnable `examples/statistical_diagnostics.py` artifact for QQ, ECDF, and residual Vega-Lite specs.
- Diagnostic claim guidance with weak/strong QQ, residual, and ECDF wording examples.

### Changed

- README now leads with the CLI audit gate as the front door for agent-gated workflows.
- `docs/AGENT_INTEGRATION.md` now tells agents to stop on `BLOCK` and summarize `REVIEW` findings for human review.
- `ROADMAP.md` now treats v0.2.0 as a checked-off release checklist.
- CI now runs CLI smoke checks for legacy and statistical diagnostic traps.
- First-party statistical Vega-Lite specs now preserve intent metadata so `audit_spec()` can apply QQ and residual semantics.
- QQ audits now require an appropriate fitted reference line and test whether severe tail departure contradicts normality-oriented claims.
- Residual audits now test whether deterministic fitted-value structure contradicts “no pattern” or random-scatter claims.
- The README now links directly to the runnable diagnostic traps and their expected audit outcomes.

### Fixed

- Spec audits now fail when encoded fields are missing or quantitative encodings point to non-numeric data, including Vega-Lite shorthand encodings.
- Trend and distribution gates now count usable observations instead of raw rows with null metrics.
- Layered trend specs generated by `chart-contract` now receive the same completeness checks as simple line specs.
- Generated specs preserve source, unit, caveat, filters, and custom metadata in `usermeta`.
- Numeric trend axes render quantitatively instead of as equally spaced ordinal categories.
- Unsupported direct chart intents now fail audit before rendering, and data/dataset identifiers no longer create accidental decoration warnings.

### Notes

- The release remains deterministic and keeps runtime dependencies limited to pandas and Altair.
- Statistical diagnostics provide explainable guardrails, not formal normality tests or model-adequacy certification.
- Automatic chart correction, dashboards, external data fetching, and broad plotting-library coverage remain out of scope.
