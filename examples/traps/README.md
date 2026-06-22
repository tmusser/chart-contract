# CLI Trap Fixtures

These fixtures are tiny, synthetic, and meant to be run directly through the v0.2 agent gate.

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

## Notes

- The fixtures are intentionally small enough to inspect by eye.
- The claim lives in a separate text file so the spec and data stay uncluttered.
- `single_point_trend.csv` is included because the one-point trend needs real input data to trigger the gate.
