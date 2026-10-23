# Agent Integration

Use `chart-contract` as a gate before a chart is shared.

## v0.2.0 — Agent Gate

Current copy-paste CLI shape:

```bash
chart-contract audit spec path/to/spec.vl.json \
  --data path/to/data.csv \
  --claim "The launch improved conversion"
```

Supported inputs:

- `--data path/to/data.csv` for CSV input.
- `--data path/to/data.json` for JSON input.
- `--claim "..."` for the chart claim being audited when the spec does not already carry `usermeta.claim`; when both are present they must match exactly.
- `--format text|json|markdown` for the desired report shape.
- `--out path/to/report.txt` to write the selected output to disk.
- `--markdown path/to/report.md` to write Markdown output alongside the selected format.
- `--warnings-as-errors` to make REVIEW exit nonzero.
- `--fail-on READY|REVIEW|BLOCK` to set an explicit threshold; `READY` is mechanically valid but effectively means "always fail."

Gate behavior:

- `READY`: continue only while the bound inputs still match the chart being shared.
- `REVIEW`: summarize warnings, stop, and ask a human whether to proceed.
- `BLOCK`: stop immediately and fix the spec or data contract before sharing.

Policy:

- The agent must stop on `BLOCK`.
- Do not swap the claim attached to a chart artifact. If `usermeta.claim` exists, audit that claim or supply the exact same text; `contract.claim.consistency` blocks conflicting claim sources.
- When percent presentation is explicit, declare `usermeta.value_representation` as `fraction` or `percentage_points`; never infer the scale from observed values and never rescale the data merely to satisfy the audit.
- Do not assume a generic `rate` unit means percent. Preserve the actual denominator/unit semantics supplied by the analytical contract.
- Before sharing an external spec with explicit Vega-Lite transforms, inspect the `transform.inventory` findings and require `usermeta.transform_contract.declared` to exactly match the detected transform kinds.
- Treat the transform declaration as a visibility contract only. It does not mean the transform was requested, executed by chart-contract, or analytically valid.
- For transformed specs, require `transform.lineage.receipts` to pass as well as `transform.declaration`; regenerate receipts with `build_transform_lineage(spec)` after edits to transform syntax.
- Treat receipt hashes as structural identity only, not proof that expressions executed correctly or that upstream transformation lineage is complete.
- Inspect `data.coverage.usable_rows` before sharing: below 50% blocks, 50%-<90% requires review, and 90%+ only means the visible analytical fields are mostly complete.
- If `data.coverage.group_balance` warns, surface the unequal evidence retention to the human reviewer; do not infer that missingness caused the group result.
- For rank charts, require `data.rank.category_unique`, `contract.rank.truncation`, and `visual.rank.sort_order` to pass before sharing.
- Treat `data.rank.cutoff_tie` as a review signal: top-N may display more than N categories because exact cutoff ties are intentionally preserved.
- Do not summarize omitted categories as absent from the source; first-party top-N specs retain full source rows and declare how many eligible categories are omitted from display.
- For truncated ranks, require `contract.rank.comparison_set`; distinguish explicit exclusion from an explicit aggregate-Other summary.
- Treat `data.rank.omitted_metric_mass` warnings as a completeness review signal: the visible top-N may contain a minority of the total metric mass even when ranking/filter mechanics are correct.
- Treat an Other bucket as an omitted-set summary, never as a ranked category, and stop if `visual.rank.other_bucket` fails.
- When a metric catalog/version is available, preserve it in `metric_definition_contract` rather than assuming a stable field name implies stable semantics.
- Stop on `data.metric.definition_basis`: supplied rows declare incompatible metric versions and should not be compared as one metric artifact.
- A passing metric-definition contract is identity metadata, not validation that upstream SQL or Python actually implemented the declared definition.
- When a stable metric can be computed over multiple filtered/cohort universes, preserve `analysis_scope_contract` rather than assuming the field name defines scope.
- Stop on `data.analysis_scope.basis`: supplied rows carry incompatible scope identities and should not be treated as one analytical universe.
- Do not execute or rewrite arbitrary SQL/filter expressions to satisfy a scope contract; v1 checks declared identity and optional row-level basis evidence only.
- When measurement units can differ across source rows, preserve `unit_conversion_contract` instead of assuming the displayed `unit` describes raw evidence.
- Stop on `data.unit.source_basis` for mixed source units and on `data.unit.conversion_evidence` when a fixed factor does not reproduce supplied source/display values.
- Do not fetch FX, normalize units, or rewrite values to satisfy the audit; v1 supports identity and one explicit fixed multiplicative factor only.
- If the source distinguishes observed, structural-zero, missing, and suppressed metric values, preserve `observation_status_contract`; fail on zero-filled missing/suppressed evidence and stale counts rather than auto-fixing the values.
- When an artifact represents a sample or census, preserve `population_contract`; do not assume supplied rows define the population by themselves.
- Do not use DataFrame row count as `sample_size` unless `sample_member_field` proves one row per sampled unit.
- Surface `contract.population.scope` REVIEW when a claim explicitly says `sample of`, `sampled from`, `survey respondent(s)`, or `census of` without population metadata; do not generalize this into broad claim NLP.
- Surface `claim.population.generalization` REVIEW for explicit population generalization from convenience/quota/unknown/other sampling rather than silently endorsing the inference.
- A passing `data.population.weights` finding validates weight values only, not the weighting methodology or representativeness.
- Preserve `uncertainty_contract` when trend/compare charts show error bars; do not describe generic visible intervals as confidence/credible/prediction intervals without explicit metadata.
- Stop on `data.uncertainty.bounds` or `visual.uncertainty.interval`: malformed bounds or metadata detached from the visible error-bar fields invalidate the artifact.
- Narrow explicit wording such as `95% CI` must match interval kind/level; do not generalize this parser into open-ended significance or uncertainty NLP.
- Never translate interval overlap/non-overlap into a significance claim unless a separate supported inferential contract exists.
- When component evidence is expected to reconcile to an authoritative scalar, preserve `reconciliation_contract` instead of assuming the component set is complete.
- Stop on `data.reconciliation.total`; surface the residual/represented share and do not create an Unknown balancing bucket automatically.
- Treat a passing reconciliation as arithmetic consistency against the declared control only. It does not validate control-source authority, component taxonomy, or upstream joins/filters.
- For percent/rate/ratio metrics, surface `contract.ratio.denominator` warnings instead of guessing what the metric is “of.”
- If `data.ratio.denominator_basis` fails, do not compare the rows as one common metric; the supplied evidence declares incompatible denominator meanings.
- A passing denominator/cohort contract is metadata consistency, not validation of upstream SQL arithmetic or population membership.
- If a claim states an explicit numeric percent, percentage-point, or ratio change, require a comparison baseline contract before sharing.
- Stop on `contract.comparison.change` or `claim.comparison.change_semantics` failures; do not rewrite arithmetic labels merely to make the audit pass.
- Treat a passing baseline contract as arithmetic reproducibility against supplied evidence, not proof the baseline controls seasonality, cohort drift, or causal comparability.
- Preserve `directionality_contract` when claims use better/worse semantics; do not assume that a positive numeric change is beneficial.
- Stop on `claim.metric.directionality` failures such as lower-is-better latency rising while the claim says it improved.
- Keep descriptive `increased` / `decreased` wording separate from evaluative semantics; directionality does not itself infer targets, thresholds, utility functions, or optimization policy.
- Preserve `target_contract` when an artifact claims one selected observation met or missed a scalar target; do not choose the latest/rightmost row automatically.
- Stop on `data.metric.target_observation` or `visual.metric.target`: stale selected-value receipts or a detached threshold line invalidate the target artifact.
- Narrow met/missed-target wording must match recomputed target status. A passing target contract does not validate target authority, materiality, or statistical significance.
- If repeated displayed keys appear, require a source-grain declaration before sharing; do not assume duplicate rows are harmless.
- Stop on `data.grain.unique`: duplicate declared grain keys can indicate join fanout and must not be silently deduplicated or summed away.
- For external aggregate specs, require `contract.grain.aggregation` plus the existing transform declaration/lineage checks to pass.
- For date-like baseline comparisons, require `contract.time_window.period` before sharing rather than guessing month/rolling/MTD semantics from labels.
- Stop on complete-vs-incomplete or unequal rolling-window failures; do not silently prorate totals or rewrite the period definition.
- Treat unequal complete calendar durations as REVIEW: February vs March may both be valid months even though exposure-sensitive totals need human judgment.
- First-party rendered specs carry `usermeta.claim` automatically. That metadata preserves claim identity; it does not prove the claim is supported.
- `REVIEW` means summarize the warnings and ask for human review before continuing.
- A durable audit report is valid only for its recorded `input_binding`; if the spec, explicit data, or claim changes, rerun the audit before sharing.
- `--fail-on` is available when you want an explicit threshold, but `BLOCK` is usually the practical gate.

This command prints the selected format to stdout by default.
When `--out` is supplied, the selected output is written to disk and stdout becomes a one-line verdict summary.
When `--markdown` is supplied, Markdown is also written to the requested path.

JSON and Markdown reports include deterministic input and report bindings over the audited subject, explicit data, claim, package version, saved findings/verdict, and semantic audit-profile identity. This lets downstream code detect post-audit mutation or stale policy semantics; it does not make the verdict scientifically valid or human-approved.

This is a gate, not a publisher. It is meant to keep the agent inside a bounded audit loop before anything is shared.

The working pattern is:

1. The agent proposes a chart.
2. `chart-contract` audits the spec and data contract and records input, result, and audit-profile bindings.
3. The agent fixes the chart or stops.
4. If any audited input changes, the agent reruns the audit rather than reusing the old report.
5. Immediately before sharing, the agent verifies that the report still corresponds to the current inputs.
6. A human reviews the result before sharing.

Python callers can perform the final identity check directly:

```python
report = audit_spec(spec=spec, data=df)  # uses usermeta.claim when present
if not report.matches_spec(spec=spec, data=df, claim=None):
    raise RuntimeError("audit report is stale; rerun chart-contract")
```

For first-party charts, use `report.matches_chart(chart)`.

Copy/paste instruction for agents:

> Generate a chart only if chart-contract audit passes. Preserve the exact claim carried by the chart artifact; never audit it under a different claim. If there are WARN findings, summarize them and ask whether to proceed. If there are FAIL findings, do not render for sharing; fix the spec or explain why it failed. Do not reuse an audit report after changing the spec, data, claim, saved findings/verdict, or audit-policy semantics; rerun the audit and verify the durable bindings immediately before sharing.

Allowed:

- Generate a draft chart spec.
- Run audit.
- Verify report integrity, audit-profile identity, and the input binding before sharing.
- Explain warnings.
- Propose fixes.

Not allowed:

- Ignore FAIL findings.
- Reuse a stale `READY` report after changing audited inputs.
- Claim causality without evidence.
- Hide missing source/unit.
- Auto-publish.

`chart-contract` is a review gate, not an autonomous chart publisher. It helps an agent surface evidence, caveats, visual-risk issues, and stale-audit drift before a human decides whether the chart should go out.
