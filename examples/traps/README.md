# CLI Trap Fixtures

These fixtures are tiny, synthetic, and meant to be run directly through the agent gate.

Each trap keeps the spec, data, and claim text separate so the failure mode stays easy to inspect.

## Fixtures

### `control_total_gap`

Demonstrates a clean regional revenue decomposition whose supplied components total 9.1M
against an independently declared company control total of 11.8M.

Expected verdict: `BLOCK`

```bash
chart-contract audit spec examples/traps/control_total_gap.vl.json \
  --data examples/traps/control_total_gap.csv \
  --claim "$(cat examples/traps/control_total_gap.claim.txt)"
```

Expected findings: `contract.reconciliation.control_total=PASS`,
`data.reconciliation.components=PASS`, and `data.reconciliation.total=FAIL` reporting a
2.7M residual and 77.1% represented share. The audit does not synthesize an Unknown/balancing
component.

### `interval_claim_mismatch`

Demonstrates a visually valid interval whose metadata declares a 90% credible interval while
the claim calls it a 95% confidence interval.

Expected verdict: `BLOCK`

```bash
chart-contract audit spec examples/traps/interval_claim_mismatch.vl.json \
  --data examples/traps/interval_claim_mismatch.csv \
  --claim "$(cat examples/traps/interval_claim_mismatch.claim.txt)"
```

Expected finding: `claim.uncertainty.semantics` reporting that the explicit claim kind/level
does not match the declared interval contract. The audit does not infer statistical
significance from the interval.

### `convenience_sample_generalized`

Demonstrates a structurally coherent convenience sample that explicitly generalizes its
observed result to the full target population.

Expected verdict: `REVIEW`

```bash
chart-contract audit spec examples/traps/convenience_sample_generalized.vl.json \
  --data examples/traps/convenience_sample_generalized.csv \
  --claim "$(cat examples/traps/convenience_sample_generalized.claim.txt)"
```

Expected finding: `claim.population.generalization` warning on `convenience` sampling.
The audit does not claim the sample is invalid; it requires human review before population
generalization.

### `mixed_measurement_units`

Demonstrates a visually ordinary regional revenue chart labeled USD while the supplied
row-level source-unit evidence contains both USD and EUR.

Expected verdict: `BLOCK`

```bash
chart-contract audit spec examples/traps/mixed_measurement_units.vl.json \
  --data examples/traps/mixed_measurement_units.csv \
  --claim "$(cat examples/traps/mixed_measurement_units.claim.txt)"
```

Expected finding: `data.unit.source_basis` reporting mixed source units. The audit does not
guess an FX rate or convert the EUR row.

### `too_many_pie_categories`

Demonstrates an arc chart with too many categories.

Expected verdict: `BLOCK`

```bash
chart-contract audit spec examples/traps/too_many_pie_categories.vl.json \
  --data examples/traps/too_many_pie_categories.csv \
  --claim "$(cat examples/traps/too_many_pie_categories.claim.txt)"
```

### `causal_claim_missing_caveat`

Demonstrates a causal claim without a caveat or declared causal evidence.

Expected verdict: `REVIEW`

```bash
chart-contract audit spec examples/traps/causal_claim_missing_caveat.vl.json \
  --data examples/traps/causal_claim_missing_caveat.csv \
  --claim "$(cat examples/traps/causal_claim_missing_caveat.claim.txt)"
```

### `metric_definition_drift`

Demonstrates a clean-looking `active_users` trend whose field name, unit, source, and visual
shape stay stable while the supplied row-level metric version changes from `v1` to `v2`.

Expected verdict: `BLOCK`

```bash
chart-contract audit spec examples/traps/metric_definition_drift.vl.json \
  --data examples/traps/metric_definition_drift.csv \
  --claim "$(cat examples/traps/metric_definition_drift.claim.txt)"
```

Expected finding: `data.metric.definition_basis` reporting mixed metric versions. The audit
does not infer that a stable column name means a stable business definition.

### `majority_metric_mass_omitted`

Demonstrates a structurally valid top-2 rank whose excluded categories contain 58% of the
eligible metric mass. Ranking, filter, transform declaration, lineage, and comparison-set
receipts all agree; the issue is completeness, not tampering.

Expected verdict: `REVIEW`

```bash
chart-contract audit spec examples/traps/majority_metric_mass_omitted.vl.json \
  --data examples/traps/majority_metric_mass_omitted.csv \
  --claim "$(cat examples/traps/majority_metric_mass_omitted.claim.txt)"
```

Expected finding: `data.rank.omitted_metric_mass` reporting 58.0% omitted mass.

### `join_fanout_grain`

Demonstrates a spec whose `sum(revenue)` aggregation is fully declared and transform-lineage
bound, but the supplied source evidence violates its declared `account_id + month` grain:
account A appears twice for September.

Expected verdict: `BLOCK`

```bash
chart-contract audit spec examples/traps/join_fanout_grain.vl.json \
  --data examples/traps/join_fanout_grain.csv \
  --claim "$(cat examples/traps/join_fanout_grain.claim.txt)"
```

Expected finding: `data.grain.unique` reporting duplicate declared source-grain keys. The
audit does not deduplicate the duplicate account-month row or let the aggregate hide it.

### `full_month_vs_mtd`

Demonstrates a comparison whose baseline arithmetic is internally correct but whose exposure
windows are not comparable: September is a complete month while October covers only days 1-6.

Expected verdict: `BLOCK`

```bash
chart-contract audit spec examples/traps/full_month_vs_mtd.vl.json \
  --data examples/traps/full_month_vs_mtd.csv \
  --claim "$(cat examples/traps/full_month_vs_mtd.claim.txt)"
```

Expected finding: `data.time_window.completeness` reporting one complete and one incomplete
period. The audit does not prorate October.

### `percent_vs_percentage_points`

Demonstrates a fully declared comparison whose arithmetic is correct but whose claim uses the
wrong change semantics: `40% -> 60%` is declared and recomputed as +20 percentage points,
while the claim says “increased by 20%.”

Expected verdict: `BLOCK`

```bash
chart-contract audit spec examples/traps/percent_vs_percentage_points.vl.json \
  --data examples/traps/percent_vs_percentage_points.csv \
  --claim "$(cat examples/traps/percent_vs_percentage_points.claim.txt)"
```

Expected finding: `claim.comparison.change_semantics`.

### `mixed_denominator_basis`

Demonstrates a chart whose displayed metric is consistently labeled `conversion rate` while
the row-level denominator identity changes from `visitors` to `signups`.

Expected verdict: `BLOCK`

```bash
chart-contract audit spec examples/traps/mixed_denominator_basis.vl.json \
  --data examples/traps/mixed_denominator_basis.csv \
  --claim "$(cat examples/traps/mixed_denominator_basis.claim.txt)"
```

Expected finding: `data.ratio.denominator_basis` reporting mixed denominator identities.

### `wrong_rank_topn_filter`

Demonstrates an opt-in rank spec whose generic transform declaration and lineage receipt are
internally consistent, but whose top-N category filter selects `S4` instead of the
reproducible third-ranked category `S3`.

Expected verdict: `BLOCK`

```bash
chart-contract audit spec examples/traps/wrong_rank_topn_filter.vl.json \
  --data examples/traps/wrong_rank_topn_filter.csv \
  --claim "$(cat examples/traps/wrong_rank_topn_filter.claim.txt)"
```

Expected finding: `contract.rank.truncation` reporting that the filter does not select the
reproducible top-N category set.

### `stale_transform_lineage`

Demonstrates a spec whose transform kind declaration is still correct (`filter`) but whose
lineage receipt was generated for a different filter expression.

Expected verdict: `BLOCK`

```bash
chart-contract audit spec examples/traps/stale_transform_lineage.vl.json \
  --data examples/traps/stale_transform_lineage.csv \
  --claim "$(cat examples/traps/stale_transform_lineage.claim.txt)"
```

Expected finding: `transform.lineage.receipts` with a changed `transform[0].filter` receipt.

### `low_evidence_coverage`

Demonstrates a line chart that can still render from four complete rows even though six of ten source rows are missing the plotted metric.

Expected verdict: `BLOCK`

```bash
chart-contract audit spec examples/traps/low_evidence_coverage.vl.json \
  --data examples/traps/low_evidence_coverage.csv \
  --claim "$(cat examples/traps/low_evidence_coverage.claim.txt)"
```

Expected finding: `data.coverage.usable_rows` with `4 / 10 rows (40.0%)`.

### `undeclared_filter_transform`

Demonstrates a renderable line chart with a Vega-Lite `filter` transform that changes the displayed population without a matching transform declaration.

Expected verdict: `BLOCK`

```bash
chart-contract audit spec examples/traps/undeclared_filter_transform.vl.json \
  --data examples/traps/undeclared_filter_transform.csv \
  --claim "$(cat examples/traps/undeclared_filter_transform.claim.txt)"
```

Expected findings: `transform.inventory` and `transform.declaration`

### `missing_source_or_unit`

Demonstrates a chart with missing provenance and missing units.

Expected verdict: `REVIEW`

```bash
chart-contract audit spec examples/traps/missing_source_or_unit.vl.json \
  --data examples/traps/missing_source_or_unit.csv \
  --claim "$(cat examples/traps/missing_source_or_unit.claim.txt)"
```

### `single_point_trend`

Demonstrates a trend chart with only one observation.

Expected verdict: `BLOCK`

```bash
chart-contract audit spec examples/traps/single_point_trend.vl.json \
  --data examples/traps/single_point_trend.csv \
  --claim "$(cat examples/traps/single_point_trend.claim.txt)"
```

### `qq_heavy_tails`

Demonstrates a QQ plot whose central observations look mild while the outer quantiles depart sharply from the fitted normal line. The visual contract is complete, but the claim overstates normal compatibility.

Expected verdict: `REVIEW`

```bash
chart-contract audit spec examples/traps/qq_heavy_tails.vl.json \
  --data examples/traps/qq_heavy_tails.csv \
  --claim "$(cat examples/traps/qq_heavy_tails.claim.txt)"
```

Expected finding: `claim.qq.normality_support`

### `qq_missing_reference_line`

Demonstrates an otherwise readable QQ point plot without the fitted reference line required to interpret departures.

Expected verdict: `BLOCK`

```bash
chart-contract audit spec examples/traps/qq_missing_reference_line.vl.json \
  --data examples/traps/qq_missing_reference_line.csv \
  --claim "$(cat examples/traps/qq_missing_reference_line.claim.txt)"
```

Expected finding: `visual.qq.reference_line`

### `residual_obvious_pattern`

Demonstrates a residual plot with a strong fitted-value trend while the claim says the residuals are randomly scattered with no pattern.

Expected verdict: `REVIEW`

```bash
chart-contract audit spec examples/traps/residual_obvious_pattern.vl.json \
  --data examples/traps/residual_obvious_pattern.csv \
  --claim "$(cat examples/traps/residual_obvious_pattern.claim.txt)"
```

Expected finding: `claim.residual.pattern_support`

### `diagnostic_tiny_sample`

Demonstrates a structurally complete residual plot with only four fitted/residual pairs. The tiny sample blocks diagnostic interpretation even though the chart can render.

Expected verdict: `BLOCK`

```bash
chart-contract audit spec examples/traps/diagnostic_tiny_sample.vl.json \
  --data examples/traps/diagnostic_tiny_sample.csv \
  --claim "$(cat examples/traps/diagnostic_tiny_sample.claim.txt)"
```

Expected finding: `data.residual.sample_size`

## Notes

- The fixtures are intentionally small enough to inspect by eye.
- The claim lives in a separate text file so the spec and data stay uncluttered.
- Statistical trap specs declare `usermeta.chart_contract_intent` so `audit_spec()` can apply first-party QQ or residual semantics.
- A `REVIEW` diagnostic can be structurally complete while its claim overstates the evidence.
- A `BLOCK` diagnostic is missing required evidence, observations, or a table-stakes reference layer.
