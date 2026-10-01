# SPEC

## Objective

Build `chart-contract`, a lightweight Python harness for claim-first analytical charts that makes the claim, evidence shape, visual intent, provenance, audit-policy identity, and known limitations inspectable before a chart is shared.

The package should emit Altair/Vega-Lite output and deterministic `PASS`/`WARN`/`FAIL` findings summarized as `READY`, `REVIEW`, or `BLOCK`.

## Audience

- Analysts and analytics engineers who want auditable chart defaults.
- AI-assisted builders who need a thin contract layer before sharing charts.
- Agent workflows that need a deterministic CLI gate and durable audit report.

## Current Scope

- descriptive intents: `Chart.trend()`, `Chart.rank()`, and `Chart.compare()`
- distribution intents: `Chart.histogram()`, `Chart.boxplot()`, and `Chart.violin()`
- statistical diagnostic intents: `Chart.qq()`, `Chart.ecdf()`, and `Chart.residual()`
- two-set membership intent: `Chart.set_membership()`
- rooted process-tree intent: `Chart.process_tree()`
- `chart.audit()` for first-party chart contracts
- experimental `audit_spec()` for supported Vega-Lite evidence shapes
- deterministic input bindings that tie public audit reports to the exact audited subject, data, claim, and historical package version
- schema `0.4` report bindings that tie saved findings/verdict semantics to the input bundle and exact audit-profile semantic identity
- machine-readable `audit-v0.2` profile metadata for the documented audit ruleset
- deterministic `audit-profile-semantics-v1` identity that separates semantic audit-policy drift from package/tool metadata drift
- `chart-contract profile show` and `chart-contract profile diff` for read-only ruleset inspection and mechanical drift
- external-spec policy checks that block undeclared quantitative scale overrides and native normalization
- explicit percent value representation via `value_representation="fraction" | "percentage_points"`, preserved in first-party spec metadata
- deterministic Vega-Lite transform inventory plus exact `usermeta.transform_contract.declared` matching for explicit analytical transforms
- `chart.to_altair()` and `chart.to_vega_lite()`
- `chart-contract audit spec` with text, JSON, and Markdown reports
- Altair/Vega-Lite as the only renderer
- deterministic, explainable audit findings and stable CLI exit behavior
- docs, tests, traps, examples, and generated proof artifacts

## Evidence Boundaries

- Trend, rank, compare, distribution, diagnostic, and membership claims require explicit fields and usable observations.
- QQ and residual charts provide visual diagnostic guardrails, not formal normality or model-adequacy certification.
- Set membership requires one row per unique universe member and exactly two explicit boolean or integer `0`/`1` membership columns.
- Venn-style circle geometry is schematic; labeled region counts are authoritative.
- Process trees require one row per unique node, exactly one root, valid parent references, non-empty labels, and no cycles; optional branch text labels incoming edges.
- Process-tree geometry is schematic: parent-child topology, direction, labels, and branch text are authoritative; box size and spacing are not quantitative.
- Arbitrary external Vega-Lite specs are audited only where the required evidence can be reconstructed deterministically.
- Quantitative scale overrides and native Vega-Lite normalization in external specs require explicit user-request declarations; the declarations are metadata boundaries, not proof that the user actually made the request.
- A nonzero quantitative bar baseline remains a visual-integrity failure even when a user-request declaration is present.
- The scale/normalization policy does not infer semantic normalization hidden in arbitrary transforms or data that was preprocessed before reaching the audited spec.
- Percent representation is never inferred from observed value ranges; `0.42` versus `42` must be declared when percent presentation is explicit.
- Generic rate units are not assumed to be percentages, and percent representation checks do not validate upstream numerator/denominator logic.
- Transform inventory records explicit operator kinds and exact spec locations but does not execute arbitrary transform expressions or reconstruct transformed output values.
- A matching transform declaration is transparency/provenance only; it does not prove analytical appropriateness, user intent, or consistency with upstream preprocessing.
- Input fingerprints prove content identity, not analytical truth, scientific validity, or human approval.
- Report-result fingerprints detect saved finding/verdict drift but are not signatures; someone with write access can deliberately recompute them.
- Audit-profile digests identify declared ruleset semantics; they do not authenticate execution, prove the implementation correct, or establish that any chart is safe or scientifically sound.
- A profile mismatch means the saved audit policy differs from the installed policy and requires re-audit for a current verification result; it does not itself classify the old or new policy as better.
- Profile diffs are mechanical only and do not classify changes as compatible, breaking, improved, or scientifically preferable.

## Non-Goals

- UI, dashboards, or Streamlit
- automatic chart correction
- renderers beyond Altair/Vega-Lite
- broad plotting-library coverage beyond explicitly supported intents
- external data fetching, LLM calls, telemetry, or theme systems
- three-or-more-set Venn diagrams or area-proportional Venn fitting
- cyclic flowcharts, multi-parent DAGs, cross-links, swimlanes, or arbitrary graph layout in the `process_tree` intent
- unverifiable claims of statistical, accessibility, or design certification
- reconstructing missing user intent from generated chart metadata
- cryptographic signing, timestamp authority, or remote attestation of audit reports
- backfilling audit-profile/result identity into historical report schema `0.3`; durable `0.4` verification requires re-audit
- automatic audit-profile compatibility classification
- general-purpose execution or validation of arbitrary Vega-Lite transform expressions

## Acceptance Criteria

- Public API supports every intent listed in Current Scope.
- Audit findings cover contract completeness, usable data, visual form, claim support, provenance, and explainable visual-integrity checks.
- Public `audit_spec()` and first-party `Chart.audit()` reports include deterministic SHA-256 input and report bindings and serialize as bound report schema `0.4`.
- Changing the audited subject, explicit data, claim, saved findings/verdict, or audit-profile semantics invalidates durable verification.
- Report binding covers the input bundle, every serialized finding, derived verdict/summary fields, and `audit-profile-semantics-v1` identity.
- Equivalent JSON mapping key order does not change a spec fingerprint.
- `chart-contract profile show audit-v0.2 --json` emits a bounded manifest covering the same stable rule IDs as `docs/AUDIT_RULES.md`.
- Package-version-only changes do not change `audit-profile-semantics-v1` identity; changes to rule semantics do.
- `chart-contract profile diff` reports profile/rule/order/tool drift without making a compatibility judgment.
- External Vega-Lite specs with explicit quantitative domain overrides or `scale.zero=false` block unless `usermeta.user_requested_scale_override=true` is declared, except truncated bars, which remain blocked.
- External Vega-Lite specs using native stack normalization block unless `usermeta.user_requested_normalization=true` is declared.
- Untouched quantitative scale defaults do not require authorization metadata.
- Percent-valued first-party charts warn when representation is missing, block malformed/unsupported declarations, preserve `usermeta.value_representation`, and never mutate the raw data.
- External percent specs warn when fractional values lack percent formatting and block percentage-point values routed through a fraction-scaling percent formatter.
- Every explicit Vega-Lite transform occurrence is inventoried by kind and exact spec location; malformed or ambiguous transform entries block.
- Specs with explicit transforms block unless `usermeta.transform_contract.declared` exactly matches the unique detected transform-kind set; stale declarations block too.
- First-party histogram and violin output carries exact transform declarations for the transforms those renderers emit.
- The CLI returns stable reports and exit codes for `READY`, `REVIEW`, and `BLOCK`.
- First-party generated specs preserve intent and evidence metadata required for downstream auditing.
- `Chart.process_tree()` blocks duplicate/null node IDs, blank labels, invalid roots, dangling parents, and cycles before rendering a deterministic top-down tree.
- Examples run on synthetic data and write inspectable Vega-Lite JSON into `examples/output/`.
- CI tests the supported Python range and validates an isolated built wheel.
- README, roadmap, changelog, and workflow artifacts describe current behavior without overstating guarantees.

## Constraints

- Python 3.10+
- Runtime dependencies limited to `pandas` and `altair`
- Simple, inspectable models and deterministic thresholds
- Explainable warnings only
- New intents require explicit data, claim, visual, test, and documentation contracts

## Verification Commands

- `python -m pip install -e ".[dev]"`
- `python -m pytest`
- `python examples/bad_to_good_chart.py`
- `python examples/distribution_charts.py`
- `python examples/statistical_diagnostics.py`
- `python examples/set_membership.py`
- `python examples/process_tree.py`
- `chart-contract profile show audit-v0.2 --json`
- `chart-contract --version`
- `git diff --check`

## Smallest Verification Demo

Run `python examples/bad_to_good_chart.py` to compare a risky chart that still renders with a corrected contract-driven chart and inspect the emitted audit evidence.

For set membership, run `python examples/set_membership.py` and verify that A-only, overlap, B-only, neither, and universe counts reconcile in the generated spec metadata.

For process trees, run `python examples/process_tree.py` and verify that the generated spec records one root, four directed edges, deterministic top-down layout metadata, and labeled Yes/No branches.

For visual defaults, run `python -m pytest tests/test_spec_policy.py` and verify that silent line-scale cropping and native normalization block while explicitly declared user-requested transformations pass their policy checks.

For audit provenance, run `python -m pytest tests/test_input_binding.py tests/test_saved_report_verification.py` and verify that unchanged artifacts reproduce their bindings while spec, data, claim, finding/verdict, and audit-profile mutations invalidate durable verification.

For audit-profile inspection, run `python -m pytest tests/test_profiles.py tests/test_profile_diff.py tests/test_cli_profile.py` and verify that the 55-rule manifest stays aligned with the rule reference, version-only drift is nonsemantic, and rule-level changes are reported mechanically.

For percent representation, run `python -m pytest tests/test_percent_semantics.py` and verify that fractional versus percentage-point values are explicit, display formatting matches the declaration, and raw values are never silently rescaled.

For Vega-Lite transforms, run `python -m pytest tests/test_transform_policy.py` and verify exact inventory locations, declaration drift failures, malformed-transform blocking, encoding-level detection, and first-party transform metadata.

## Open Questions

- What release version should carry the set-membership and process-tree intents?
- Should a future many-set intent use an UpSet-style matrix rather than circles?
- Which additional external-spec shapes can be audited without inventing missing semantic evidence?
- Should a future signed-attestation layer live outside chart-contract rather than weakening the current explicit "hashes are not signatures" boundary?
