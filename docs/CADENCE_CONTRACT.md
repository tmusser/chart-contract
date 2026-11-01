# Trend Cadence and Missing-Period Contract (v1)

A line chart can be internally valid while silently skipping a bad week or
month. This optional contract checks the sequence of **original source
observation dates** against an explicitly declared daily, weekly, or monthly
calendar frequency. It never fills gaps, aggregates duplicates, rewrites dates,
or infers a calendar from the claim.

## First-party example

```python
chart = Chart.trend(
    data=df, x="week", y="sales",
    claim="Reported weekly sales by week.",
    source="warehouse.sales", unit="systems",
    cadence_frequency="weekly",
    cadence_require_complete=False,
)
report = chart.audit()
```

Only `Chart.trend` supports this contract. Both options must be provided or
both omitted. No other constructor or legacy chart is affected.

- `cadence_frequency`: `daily`, `weekly`, or `monthly`.
- `cadence_require_complete=False`: a missing internal period `WARN`s /
  yields `REVIEW` and can be rendered with an explicit caveat.
- `cadence_require_complete=True`: any gap `FAIL`s / yields `BLOCK`;
  first-party rendering refuses the chart.
- Dates are canonical `YYYY-MM-DD` strings, unique and complete.
- **Weekly**: dates must be seven days apart on the grid anchored by the first
  observed date. A missing Monday between two Mondays is a gap; a Tuesday is
  off-grid and invalid. This makes no ISO-week-start assumption.
- **Monthly**: dates must be first-of-month, with calendar-month increments
  (February and leap years are handled). Month-end and arbitrary anchors are
  deliberately unsupported in v1.
- **Daily**: calendar-day increments.

The contract operates on the **date field displayed on the x axis**, not
`freshness_observation_date_field` or a guessed timestamp field. It checks
internal gaps between the earliest and latest supplied date; it **cannot infer
unobserved leading/trailing periods**. A single observed date is trivially
complete under this narrow definition, but ordinary trend minimum-point rules
still apply.

## Durable receipt

The first-party renderer stores a closed `usermeta.cadence_contract`:

```json
{
  "version": 1,
  "date_field": "week",
  "frequency": "weekly",
  "require_complete": true,
  "start_date": "2026-09-07",
  "end_date": "2026-09-28",
  "observed_count": 3,
  "expected_count": 4,
  "missing_count": 1,
  "missing_preview": ["2026-09-14"]
}
```

For this example, the source has observations on September 7, 21, and 28;
September 14 is absent.

`missing_preview` contains the earliest five missing dates, in chronological
order; it is not a substitute for `missing_count`. Expected periods are capped
at 10,000 to keep evidence validation bounded. The receipts are recomputed from
the supplied data on a Vega-Lite spec audit. Stale or forged counts/dates
`BLOCK`. An external contract must bind to a simple visible line chart with
ordinal/temporal date x and quantitative metric y. Layered first-party specs
are assessed using the primary analytical line.

## Rules

| Rule | PASS | WARN | FAIL |
| --- | --- | --- | --- |
| `contract.trend.cadence` | Closed valid declaration bound to trend x | — | Unsupported/malformed/detached declaration |
| `data.trend.cadence_evidence` | Dates and receipts reconstruct | — | Missing/noncanonical/duplicate/off-grid dates, stale receipts, or missing source |
| `data.trend.cadence` | All internal slots present | Missing internal slots, when completeness is optional | Missing internal slots, when completeness is required |

Only explicitly opted-in charts emit these rules. Their policy is *not* an
estimate of statistical significance, data correctness, or why observations
are missing.

## CLI trap

```bash
chart-contract audit spec examples/traps/missing_weekly_sales.vl.json \
  --data examples/traps/missing_weekly_sales.csv \
  --claim "$(cat examples/traps/missing_weekly_sales.claim.txt)"
```

The stored receipt truthfully records a missing September 14, 2026; the
`data.trend.cadence_evidence` rule passes while `data.trend.cadence` blocks
because `require_complete=true`.

## Deliberate boundaries

- No implicit `date_range`, filling a gap with zero, interpolation, smoothing,
  or imputation. A skipped week may be a source outage or a genuinely
  non-applicable observation; the check does not infer the cause.
- No assumption that every data source has a daily/weekly/monthly cadence,
  no group-level grids, and no support for trading-day/business-day/holiday
  calendars in v1.
- A sequence with an absent last week cannot be detected without an externally
  declared expected end date. Consider the separate data-freshness contract
  when a report needs an explicit `as_of` policy.
