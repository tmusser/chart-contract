# CLI Trap Fixtures

These fixtures are tiny, synthetic, and meant to be run directly through the agent gate.

Each trap keeps the spec, data, and claim text separate so the failure mode stays easy to inspect.

## Fixtures

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
