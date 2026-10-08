# Time-Window Comparability Contract

Time-based comparisons can look valid while comparing different exposure windows.

Examples:

- September full month vs October month-to-date;
- trailing 28 days vs trailing 31 days;
- February vs March raw totals;
- one complete quarter vs one partial quarter.

`chart-contract` version 1 makes those period semantics explicit for baseline comparisons.

## First-party API

```python
chart = Chart.trend(
    data=df,
    x="period",
    y="orders",
    claim="October orders are higher than September orders.",
    source="warehouse.orders",
    unit="count",
    baseline_field="period",
    baseline_value="2026-09-01",
    target_value="2026-10-01",
    change_type="absolute",
    declared_change=20,
    window_kind="calendar",
    window_granularity="month",
    baseline_start="2026-09-01",
    baseline_end="2026-09-30",
    target_start="2026-10-01",
    target_end="2026-10-31",
    baseline_complete=True,
    target_complete=True,
)
```

Version 1 supports:

- `window_kind="calendar"`
- `window_kind="rolling"`

Calendar granularities:

- day
- week
- month
- quarter
- year

Rolling windows use `window_granularity=None`.

## Complete calendar periods

A window marked complete must actually span one full declared calendar period.

Examples:

- complete month -> first day through last day of one month;
- complete quarter -> first day of quarter through last day of quarter;
- complete year -> January 1 through December 31.

A target declared as a complete October month but ending on October 6 blocks.

## Completeness

Rule: `data.time_window.completeness`

- both complete -> PASS
- one complete and one incomplete -> FAIL / BLOCK
- both incomplete -> WARN / REVIEW

The contract does not automatically prorate or normalize a partial period.

## Duration

Rule: `data.time_window.duration`

Rolling windows are duration contracts.

A trailing 28-day baseline compared to a trailing 31-day target blocks.

Calendar periods are different: February and March can both be complete months while containing
different numbers of days. Unequal complete calendar durations therefore produce REVIEW rather
than an automatic failure.

That warning matters most for exposure-sensitive totals such as:

- orders;
- revenue;
- incidents;
- sessions.

The audit does not decide whether a rate, average, or total should be normalized.

## Durable receipts

First-party specs preserve:

```json
{
  "usermeta": {
    "time_window_contract": {
      "version": 1,
      "window_kind": "calendar",
      "window_granularity": "month",
      "baseline_start": "2026-09-01",
      "baseline_end": "2026-09-30",
      "target_start": "2026-10-01",
      "target_end": "2026-10-31",
      "baseline_complete": true,
      "target_complete": true,
      "baseline_days": 30,
      "target_days": 31
    }
  }
}
```

The inclusive day counts are receipts. Spec re-audits recompute them from the declared dates and
block stale metadata.

## Missing metadata

When a comparison baseline field is date-like and a comparison contract exists but no
time-window contract is declared:

- `contract.time_window.period` -> WARN
- verdict -> at least REVIEW

The audit does not infer a full month, rolling window, or partial period from a label alone.

## Boundaries

A passing time-window contract does not prove:

- the source system finished ingesting the declared complete period;
- holidays or business-day counts are comparable;
- seasonality is controlled;
- the periods contain equivalent cohorts;
- a raw total should be normalized;
- the chosen periods are analytically fair.

Version 1 answers a narrower question:

**What exact periods were compared, are they calendar or rolling windows, are they complete,
and are their exposure durations structurally comparable without hidden normalization?**
