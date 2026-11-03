# Trend Influence and Leave-One-Out Sensitivity (v1)

A line chart can be arithmetically sound yet its apparent direction can depend
on one influential observation. This **opt-in, deterministic descriptive check**
compares the ordinary least-squares (OLS) slope on all source rows with the
slopes after independently dropping each observation, one at a time.

It catches **sign reversals**; it is **not** a p-value, confidence interval,
robust regression estimator, causal analysis, or automatic outlier removal.

## First-party usage

```python
chart = Chart.trend(
    data=weekly_sales, x="week", y="sales",
    claim="Weekly sales are shown over time.",
    source="warehouse.sales", unit="systems",
    trend_influence=True,
)
report = chart.audit()
```

Only `Chart.trend` supports this opt-in flag. When omitted or explicitly
`False`, no influence rules are emitted and legacy behavior is unchanged.
Other flag types are rejected rather than coerced.

## Scope and eligibility

- Simple unaggregated **line charts** with directly visible x and y fields;
  external Vega-Lite audits refuse unsupported transforms, aggregation, binning,
  and time-unit transforms rather than claiming to analyze displayed results.
- Between **5 and 2,000 complete source rows**, inclusive. The bound keeps
  leave-one-out evaluation inexpensive and deterministic (O(n²) v1).
- A unique independent x value per row, represented consistently as finite
  numeric values or canonical `YYYY-MM-DD` date strings. A date series is
  expressed in **days**; numeric series use the original x units.
- A finite numeric y value for every source row. No complete-case filtering,
  imputation, deduplication, interpolation, ranking, or automatic aggregation.
- No x-scale or slope inference from categorical labels, timestamps with
  implicit time zones, missing data, transformed evidence, or fitted-model
  residuals.

Source-evidence violations are `FAIL/BLOCK`, not silent exemptions.

## Numerical definition

OLS slope is calculated from centered x and y values. For each observation
`i`, compute a new OLS slope on all `n-1` remaining observations.
`stat.trend.influence` warns when the full-data slope is definitively
positive and at least one leave-one-out slope definitively negative, or vice
versa.

To avoid labelling floating-point noise as a reversal, a slope is considered
numerically flat when:

```text
abs(slope) <= 1e-10 * (max(y) - min(y)) / (max(x) - min(x))
```

A flat full-data slope or a flat leave-one-out slope does **not** count as a
sign reversal. The tolerance is numerical bookkeeping, not a business-impact
threshold or a statistically motivated confidence bound. Slope sign does not
establish statistical significance or substantive importance.

## Durable receipts

The renderer embeds the closed `usermeta.trend_influence_contract`:

```json
{
  "version": 1,
  "x_field": "week",
  "y_field": "sales",
  "x_kind": "date",
  "row_count": 6,
  "full_slope": 0.3673469387755102,
  "loo_min_slope": -0.14285714285714285,
  "loo_max_slope": 0.5714285714285714,
  "flat_tolerance": 6.857142857142858e-11,
  "reversal_count": 1,
  "reversal_preview": ["2026-10-12"]
}
```

`reversal_preview` lists up to five omitted x values in chronological or
numeric order; the full count is stored separately. External Vega-Lite audits
recompute every numeric and categorical receipt from the original supplied
rows. Missing, malformed, forged, or stale receipts `FAIL/BLOCK`. A PASS
means supplied-row consistency, not that the source or claim is trustworthy.

## Audit rule outcomes

| Rule | PASS | WARN | FAIL |
| --- | --- | --- | --- |
| `contract.trend.influence` | Closed v1 declaration binds a visible untransformed line | — | Missing, malformed, or detached binding |
| `data.trend.influence_evidence` | Source and leave-one-out receipts reproduce | — | Invalid evidence, duplicate x, insufficient/too many rows, or stale receipts |
| `stat.trend.influence` | No sign reversal beyond tolerance | At least one omitted observation reverses slope direction | — |

Warnings yield `REVIEW`; use `--warnings-as-errors` to make them a nonzero
CLI gate. No user data is rewritten.

## Reproducible trap

```bash
chart-contract audit spec examples/traps/influential_weekly_sales.vl.json \
  --data examples/traps/influential_weekly_sales.csv \
  --claim "$(cat examples/traps/influential_weekly_sales.claim.txt)"
```

The six weekly sales figures are `10, 9, 8, 7, 6, 30`. The full-data OLS
trend is positive, but excluding October 12 yields a negative slope.
The source/receipt check PASSES; `stat.trend.influence` WARNS; overall verdict
is `REVIEW`.

## What this check does not establish

It does not test significance, confidence or prediction intervals,
autocorrelation, stationarity, drift, structural breaks, seasonality, robust
trend estimates, statistical leverage metrics like Cook's distance, or
whether the omitted observation is an error. Those need separate inferential
or domain-aware contracts. A sign-stable trend can still be misleading, and
a sign reversal does not prove a trend is wrong or that any observation should
be removed.
