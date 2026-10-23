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
- deterministic evidence-coverage checks over visible analytical fields, including usable-row retention and grouped missingness imbalance
- occurrence-level transform lineage receipts binding exact transform payloads plus bounded input/output field lineage
- explicit rank/top-N contracts with unique categories, descending order, tie-safe cutoff expansion, and omitted-category receipts
- explicit comparison-set completeness for truncated ranks, including exclusion/aggregate-Other behavior and omitted metric-mass receipts
- explicit numerator/denominator/cohort contracts for ratio-like trend/rank/compare metrics, plus optional row-level denominator-basis consistency checks
- explicit trend/compare baseline contracts distinguishing absolute delta, percentage points, percent change, and ratio arithmetic with durable observed-value receipts
- explicit calendar/rolling comparison-window contracts with exact ISO boundaries, completeness declarations, and inclusive-day receipts
- explicit source/output grain contracts for descriptive charts, including source-key uniqueness and bounded encoding-level aggregation semantics
- explicit metric-definition identity for trend/rank/compare metrics, including stable ID/definition/version metadata and optional row-level version checks
- explicit analysis-scope identity for trend/rank/compare metrics, including stable filtered/cohort universe ID/definition/version metadata and optional row-level scope-basis checks
- explicit observation-status contracts for trend/rank/compare metrics, distinguishing observed values, structural zeros, missing values, and suppressed values with evidence-bound state counts
- explicit source/display measurement-unit contracts for trend/rank/compare metrics, including identity/fixed-scale semantics, row-level source-unit checks, and recomputable fixed conversion arithmetic
- explicit population/sample scope contracts for trend/rank/compare metrics, including declared population/sample counts, bounded sampling methods, optional row-level member/weight evidence, and explicit population-generalization intent
- explicit uncertainty interval contracts for trend/compare metrics, binding the shown estimate to lower/upper fields, interval kind, level, method, and visible interval marks
- explicit control-total reconciliation contracts for additive rank/compare component evidence, including scalar control identity, optional control source/tolerance, and durable component-total/residual/share receipts
- explicit metric-directionality contracts for trend/compare evidence, binding the shown metric to higher-is-better, lower-is-better, or neutral semantics and narrow evaluative claim parity
- explicit scalar metric-target contracts for trend/compare evidence, binding one selected observation to an at-least/at-most/equal threshold, optional absolute tolerance, visible target rule, and narrow met/missed claim parity
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
- Ratio contracts make numerator/denominator/cohort identity inspectable but do not recompute rates, validate upstream arithmetic, or prove source-population completeness.
- A denominator basis field validates supplied semantic labels only; it does not prove each row belongs to the declared cohort or denominator population.
- Comparison contracts verify selector identity and arithmetic against supplied evidence; they do not prove the chosen baseline controls seasonality, cohort drift, confounding, or other comparability threats.
- Claim comparison parsing is deliberately narrow to explicit numeric percent, percentage-point, and ratio phrases; general comparative prose is not machine-adjudicated.
- Time-window contracts verify declared boundaries, completeness state, and exposure duration only; they do not prove source ingestion completeness, seasonality control, business-day equivalence, or cohort comparability.
- Unequal complete calendar periods are reviewable rather than automatically invalid because legitimate months/quarters can differ in day count; no automatic normalization is performed.
- Grain contracts verify row-key uniqueness and declared source-to-output collapse only; they do not prove the business key, join logic, or chosen reducer is substantively correct.
- Metric-definition contracts verify declared identity/version consistency only; they do not prove the business definition is substantively correct or that upstream computation implemented it.
- Metric identity is never inferred from field names, titles, claims, units, or source strings; the contract is opt-in.
- Analysis-scope contracts verify declared filtered/cohort universe identity only; they do not execute or validate arbitrary SQL predicates, cohort logic, or upstream filter application.
- Scope identity is never inferred from a stable metric field, source string, title, or existing free-form filters metadata; the scope contract is opt-in.
- Unit conversion contracts verify declared source/display identity and fixed multiplicative arithmetic only; they do not validate external FX provenance, inflation methodology, time-varying rates, or offset conversions.
- Unit identity is never inferred from value ranges, geography, field names, or displayed labels, and chart-contract does not silently mutate source values to satisfy a conversion contract.
- Population contracts make sample/census scope explicit but do not prove the target population, sampling frame, representativeness, nonresponse assumptions, or statistical validity of population inference.
- Declared sample size is not inferred from DataFrame row count; only an explicit sample-member field can make row-level sample-count evidence reconstructable.
- Sampling weights are checked only for complete positive finite values; chart-contract does not certify calibration, design effects, or variance estimation.
- Population generalization is explicit metadata in v1 rather than open-ended claim-text inference; nonprobability generalization produces a review signal rather than automatic statistical rejection.
- Missing population metadata produces REVIEW only for bounded explicit sampling phrases (`sample of`, `sampled from`, `survey respondent(s)`, `census of`); broad population-language NLP remains out of scope.
- Uncertainty contracts verify interval field identity, complete finite bound ordering, visible lower/upper field binding, and narrow explicit claim parity only; they do not validate estimator assumptions, nominal coverage, calibration, or statistical significance.
- Interval claim parsing is deliberately narrow to explicit forms such as `95% CI`, `95% confidence interval`, `90% credible interval`, `80% prediction interval`, and `95% bootstrap interval`.
- Interval overlap/non-overlap is never converted into a hypothesis-test or significance conclusion.
- Reconciliation contracts verify arithmetic consistency between supplied unique component evidence and one declared scalar control total; they do not prove the control source is authoritative or the component taxonomy is substantively complete.
- Reconciliation uses fixed sum semantics only in v1 and rejects percent/rate/ratio metrics; chart-contract never fabricates Unknown/Other/balancing components to force equality.
- Reconciliation covers the supplied component evidence and does not replace independent top-N/comparison-set omission semantics for truncated rank displays.
- Directionality contracts bind one visible quantitative metric to higher-is-better, lower-is-better, or neutral semantics; they do not prove the metric is a valid optimization target or that utility is monotonic outside the declared comparison.
- Better/worse claim parsing is deliberately narrow to improvement/worsening wording. Descriptive increase/decrease language is not treated as an evaluative judgment.
- Evaluative directionality requires an explicit comparison baseline; chart-contract does not infer targets, thresholds, acceptable ranges, or utility functions.
- Target contracts select one exact supplied observation and compare it to one finite scalar target using at-least, at-most, or equal semantics with optional absolute tolerance; they do not infer the latest row or reporting point.
- Target receipts preserve the selected observed value, signed target gap, and recomputed target-met boolean; matching receipts do not prove the threshold is authoritative, material, achievable, or statistically meaningful.
- Target metadata must remain visibly bound to a scalar rule in audited specs; chart-contract does not silently preserve detached target metadata after the threshold line changes.
- Met/missed-target claim parsing is deliberately narrow; above/below target, on-track, healthy, acceptable ranges, and broad goal language remain outside v1.
- Transform inventory records explicit operator kinds and exact spec locations but does not execute arbitrary transform expressions or reconstruct transformed output values.
- A matching transform declaration is transparency/provenance only; it does not prove analytical appropriateness, user intent, or consistency with upstream preprocessing.
- Evidence coverage measures complete-case visibility for audited fields only; it does not establish missingness mechanism, representativeness, source quality, or absence of bias.
- Observation states are explicit supplied metadata: missing/suppressed rows must remain null, structural zeros must equal numeric zero, and status counts must reproduce; a passing contract does not prove upstream missingness logic or a particular Vega-Lite gap depiction.
- Group coverage imbalance is a review signal only and does not establish that missingness caused an observed group difference.
- Transform lineage receipts are structural identity metadata only; they do not prove expression execution, analytical correctness, or upstream SQL/Python/dbt provenance.
- Rank truncation metadata is reproducible against supplied evidence but does not prove the externally supplied category population is complete or that top-N is the best presentation.
- Omitted metric-mass shares are completeness receipts only; the 50% review threshold does not define universal business materiality.
- Aggregate-Other uses explicit sum semantics only and does not prove the ranked metric is substantively additive; ratio-like metrics are rejected from this path.
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
- statistical imputation, missingness-mechanism classification, or automatic correction of incomplete evidence
- automatic conversion of missing/suppressed values into zeros, inferred structural zeros, suppression approval, or verification of visual gap glyphs
- execution tracing or attestation of upstream transformation systems
- implicit aggregation of duplicate rank categories or hidden arbitrary tie-breaking at top-N cutoffs
- automatic reconstruction or recomputation of ratio numerators, denominators, cohorts, or upstream rate arithmetic
- automatic choice of analytical baselines, hidden row-order baselines, or open-ended natural-language interpretation of comparison claims
- automatic prorating, exposure normalization, or inference of MTD/full-period/rolling semantics from labels alone
- automatic deduplication, join-fanout repair, or guessing sum/mean/other aggregation when source grain is finer than displayed grain
- inference of business metric definitions or automatic reconciliation of rows produced under different metric versions
- execution, normalization, or semantic equivalence checking of arbitrary SQL/filter/cohort predicates merely to validate analysis scope
- automatic unit conversion, FX lookup, inflation adjustment, time-varying conversion factors, or affine/offset conversion such as Celsius/Fahrenheit
- automatic representativeness certification, survey-design validation, sample-frame completeness proof, response-bias correction, weight calibration, or statistical population-generalization approval
- automatic confidence/credible/prediction/bootstrap interval computation, coverage certification, significance testing, p-value inference, or overlap-based hypothesis conclusions
- automatic balancing buckets, accounting adjustments, control-total source authentication, or inference that a metric is additive merely because a sum reconciliation was declared
- automatic optimization policy, metric-target selection, acceptable-range inference, utility-curve inference, or treating every numeric increase/decrease as a better/worse judgment
- automatic latest-row target selection, target-authority certification, target materiality/achievability judgment, multi-threshold bands, dynamic targets, or broad natural-language goal interpretation

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
- Chart/spec evidence coverage PASSes at 90%+ complete rows across visible analytical fields, WARNs from 50% to below 90%, and FAILs below 50%.
- Grouped evidence with at least two eligible groups of five source rows each WARNs when usable-row coverage differs by at least 20 percentage points.
- Coverage excludes tooltip-only fields from the main visible-evidence denominator and is not fabricated when required fields are absent or transform-derived output cannot be reconstructed.
- Every auditable transform occurrence in a passing transformed spec has an exact version-1 lineage receipt; same-kind payload edits, missing receipts, malformed receipts, and stale receipts block.
- Rank charts require one row per non-null category, deterministic descending metric order, and explicit top-N intent; cutoff ties are included rather than silently split.
- First-party top-N rank specs preserve the full supplied rows, declare eligible/displayed/omitted category counts, and use one bounded category filter whose selected set is reproducible from the supplied evidence.
- Truncated ranks declare exclude vs aggregate-Other behavior; comparison-set receipts reconcile eligible/selected/omitted metric totals and shares where meaningful.
- Explicit exclusion WARNs when omitted non-negative metric mass is at least 50%; aggregate-Other sums exactly the omitted categories, remains source-reconstructable, and is pinned after ranked categories.
- Ratio-like trend/rank/compare metrics WARN when numerator/denominator identity is absent; malformed or partial declared ratio contracts block.
- First-party specs preserve a closed version-1 ratio contract binding the shown metric to numerator, denominator, optional cohort, and optional denominator basis field.
- When a denominator basis field is declared, missing/null/mixed identities or a basis identity that disagrees with the declared denominator block.
- Trend/compare comparison contracts identify one visible baseline field plus distinct baseline/target selector values; each selector must resolve to exactly one finite numeric metric observation.
- Declared absolute, percentage-point, percent-change, or ratio changes must match deterministic recomputation; first-party specs preserve baseline/target values and computed change as durable receipts.
- Explicit numeric claim wording for percent, percentage points, or ratios must match the declared comparison type and value; missing baseline metadata for such wording produces review rather than inferred semantics.
- Date-like baseline comparisons without explicit time-window metadata WARN; declared windows use canonical ISO dates and closed version-1 calendar/rolling semantics.
- Complete-vs-incomplete time comparisons block; two incomplete windows require review; unequal rolling durations block while unequal calendar durations warn.
- Complete calendar windows must span one full declared day/week/month/quarter/year period; first-party specs preserve recomputable inclusive-day receipts.
- Declared source-grain fields must exist, be non-null, and uniquely identify every supplied row; duplicate grain keys block rather than being silently deduplicated.
- First-party descriptive charts refuse many-to-one source-to-display collapse; external specs may use one supported encoding-level aggregate only when grain metadata exactly matches the aggregate and recomputed row/group receipts.
- Declared metric-definition contracts bind the shown quantitative field to one metric ID, definition, and version; partial/malformed/field-mismatched contracts block.
- When a metric basis field is declared, missing/null/mixed row versions or versions that disagree with the contract block.
- Declared analysis-scope contracts bind the artifact to one non-empty scope ID, definition, and version; partial/malformed contracts block.
- Optional scope-basis field/value declarations must be paired, and every supplied row must carry one non-empty scope identity exactly matching the declared basis value.
- Declared unit-conversion contracts bind the shown quantitative field to source/display units and either identity or fixed-scale semantics; malformed, partial, field-mismatched, or display-unit-mismatched contracts block.
- When a source-unit basis field is declared, missing/null/mixed/mismatched source-unit identities block; fixed-scale conversions must reproduce displayed values from preserved source values and the declared factor.
- Explicit `sample of` / `sampled from` / `survey respondent(s)` / `census of` claim wording without population metadata produces REVIEW; ordinary claims do not invent sampling semantics.
- Declared population contracts distinguish sample versus census scope, require coherent population/sample counts and sampling methods, and preserve explicit population-generalization intent.
- Optional sample-member evidence must be complete, unique, and exactly reproduce declared sample size; optional weight evidence must be complete, numeric, finite, and strictly positive.
- Explicit population generalization from convenience, quota, unknown, or other nonprobability sampling methods produces REVIEW without claiming statistical invalidity.
- Declared uncertainty contracts on trend/compare charts bind the shown estimate to distinct lower/upper fields, one supported interval kind, finite level in (0,1), and explicit method; malformed or partial contracts block.
- Interval evidence must be complete, numeric, finite, and satisfy `lower <= estimate <= upper` for every supplied observation.
- First-party interval specs visibly bind the declared lower/upper fields; external specs with detached or missing interval marks block.
- Narrow explicit interval wording without metadata produces REVIEW, while declared kind/level mismatches block; passing interval metadata never implies significance or calibrated coverage.
- Declared reconciliation contracts on rank/compare component evidence bind one visible component field and one additive quantitative metric to a finite control total with optional non-negative absolute tolerance.
- Reconciliation component labels must be complete and unique and metric values finite numeric; durable component-count/sum/residual/share receipts must match supplied evidence.
- Reconciliation outside tolerance blocks and exposes the residual/represented share when meaningful; ratio-like sum reconciliation and automatic balancing buckets are not supported.
- Declared directionality contracts bind the shown quantitative field to higher-is-better, lower-is-better, or neutral semantics; malformed/unsupported/field-mismatched contracts block.
- Within explicit comparisons, narrow evaluative better/worse wording without directionality produces REVIEW; when directionality is declared, evaluative wording without an explicit comparison baseline also produces REVIEW; contradictory observed movement blocks.
- Neutral directionality rejects evaluative better/worse claims, while descriptive increase/decrease wording remains outside the directionality claim parser.
- Declared metric-target contracts bind one visible quantitative metric to one explicit selector, finite scalar target, supported operator, optional non-negative absolute tolerance, and durable selected-observation receipts.
- Target selectors must resolve to exactly one finite metric observation; first-party trend/compare specs render the declared scalar target as a visible rule and external target metadata detached from that rule blocks.
- Narrow met/missed-target wording without metadata produces REVIEW; wording that disagrees with recomputed target status blocks, while ordinary claims do not invent target semantics.
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

For audit-profile inspection, run `python -m pytest tests/test_profiles.py tests/test_profile_diff.py tests/test_cli_profile.py` and verify that the 105-rule manifest stays aligned with the rule reference, version-only drift is nonsemantic, and rule-level changes are reported mechanically.

For percent representation, run `python -m pytest tests/test_percent_semantics.py` and verify that fractional versus percentage-point values are explicit, display formatting matches the declaration, and raw values are never silently rescaled.

For Vega-Lite transforms, run `python -m pytest tests/test_transform_policy.py` and verify exact inventory locations, declaration drift failures, malformed-transform blocking, encoding-level detection, and first-party transform metadata.

For evidence coverage, run `python -m pytest tests/test_evidence_coverage.py` and verify the 90% PASS boundary, 50% BLOCK boundary, grouped 20-point review threshold, tooltip exclusion, and missing-field non-duplication.

For transform lineage, run `python -m pytest tests/test_transform_lineage.py tests/test_transform_policy.py` and verify exact operation digests, bounded field lineage, stale-receipt blocking, and first-party receipt parity.

For rank/top-N semantics, run `python -m pytest tests/test_rank_contract.py` and verify duplicate-category blocking, descending sort parity, full-source preservation, omitted-category reconciliation, bounded-filter parity, and cutoff-tie expansion.

For denominator/cohort semantics, run `python -m pytest tests/test_ratio_contract.py` and verify missing-contract review, closed-schema validation, first-party metadata preservation, mixed-basis blocking, quantitative metric binding, and unreconstructable basis evidence blocking.

For comparison-baseline semantics, run `python -m pytest tests/test_comparison_contract.py` and verify baseline uniqueness, percent-vs-percentage-point distinctions, percent-change/ratio zero-baseline blocking, stored receipt parity, and explicit claim-language mismatches.

For time-window comparability, run `python -m pytest tests/test_time_window_contract.py` and verify missing-window review, calendar boundary validation, complete-vs-partial blocking, rolling-duration parity, unequal-calendar review, and stale day-count receipt blocking.

For aggregation grain semantics, run `python -m pytest tests/test_grain_contract.py` and verify source-grain uniqueness, repeated-display-key review, first-party no-implicit-aggregation behavior, exact external encoding-aggregate matching, and stale receipt blocking.

For comparison-set completeness, run `python -m pytest tests/test_rank_contract.py` and verify explicit exclusion receipts, majority-omitted review, aggregate-Other source preservation, ratio-like blocking, Other-label collision, receipt tampering, and transform tampering.

For metric-definition identity, run `python -m pytest tests/test_metric_definition_contract.py` and verify closed-schema validation, quantitative-field binding, stable row-level version identity, mixed-version blocking, missing-evidence blocking, and opt-in no-inference behavior.

For analysis-scope identity, run `python -m pytest tests/test_analysis_scope_contract.py` and verify closed-schema validation, metadata-only scope identity, paired basis declarations, mixed-scope blocking, renderer refusal, external evidence requirements, and opt-in no-inference behavior.

For unit-conversion semantics, run `python -m pytest tests/test_unit_conversion_contract.py` and verify source-unit identity, fixed-scale recomputation, malformed-contract blocking, external binding, and stale arithmetic refusal.

For population/sampling semantics, run `python -m pytest tests/test_population_sampling_contract.py` and verify explicit-sample-claim missing-contract review, sample/census coherence, aggregated-row/sample-size separation, optional member-count reconstruction, positive-weight checks, nonprobability generalization review, external evidence requirements, and closed-schema enforcement.

For uncertainty intervals, run `python -m pytest tests/test_uncertainty_contract.py` and verify bound containment, malformed-contract blocking, first-party visible interval rendering, external visual-binding tamper detection, explicit claim kind/level parity, grouped compare intervals, and no missing-metadata inference beyond narrow interval wording.

For control-total reconciliation, run `python -m pytest tests/test_reconciliation_contract.py` and verify exact/tolerance reconciliation, residual/share receipts, duplicate-component blocking, ratio-like rejection, external receipt parity, and no automatic balancing bucket.

For metric directionality, run `python -m pytest tests/test_directionality_contract.py` and verify lower/higher-is-better claim parity, neutral semantics, missing-contract/baseline review, descriptive increase/decrease non-inference, external field binding, and closed-schema enforcement.

For metric targets, run `python -m pytest tests/test_target_contract.py` and verify scalar target operators/tolerance, exact selected-observation reconstruction, durable receipt parity, visible threshold-rule binding, missing-contract review, met/missed claim blocking, and closed-schema enforcement.

For observation-state semantics, run `python -m pytest tests/test_observation_status_contract.py` and verify true zero preservation, null state evidence, stale receipts, detached field rejection, and zero-filled missing traps.

## Open Questions

- What release version should carry the set-membership and process-tree intents?
- Should a future many-set intent use an UpSet-style matrix rather than circles?
- Which additional external-spec shapes can be audited without inventing missing semantic evidence?
- Should a future signed-attestation layer live outside chart-contract rather than weakening the current explicit "hashes are not signatures" boundary?
