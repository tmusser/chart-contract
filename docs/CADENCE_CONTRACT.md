# Trend Cadence and Missing-Period Contract (v1/v2)

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

Only `Chart.trend` supports this contract. Both frequency and completeness
options must be provided or both omitted; v2 optionally adds the explicit
expected start and/or end. Other constructors and legacy charts are unchanged.

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
internal gaps between the earliest and latest supplied date; v1 **cannot infer
unobserved leading/trailing periods** without explicit v2 endpoints. A single observed date is trivially
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

## Explicit reporting-window boundaries (v2)

V1 retains the existing internal-gap audit and exact receipt fields. V2 is
selected only when the caller declares `cadence_expected_start` and/or
`cadence_expected_end`, and enables `data.trend.cadence.boundaries`.

```python
chart = Chart.trend(
    data=frame, x="week", y="sales",
    claim="Reported weekly sales through October 26.",
    source="warehouse.sales", unit="systems",
    cadence_frequency="weekly",
    cadence_require_complete=True,
    cadence_expected_end="2026-10-26",
)
```

With observed dates October 5, 12 and 19, internal cadence PASSES while the
boundary rule FAILS: October 26 is explicitly required but missing. When
`require_complete=False`, the same gap generates WARN/REVIEW.
The first-party renderer refuses required-complete charts with missing
boundary slots.

Both endpoints are independently optional. A missing endpoint has **no
implicit value**, including no assumption about today. Dates must use
canonical `YYYY-MM-DD`; `expected_start` cannot follow the first
observation and `expected_end` cannot precede the last. Weekly dates must
lie on the seven-day grid anchored by `expected_start` when provided, or
by the first observed date otherwise. Monthly endpoints must be the first
day of a calendar month; daily dates advance by one day.
Invalid and off-grid endpoints fail instead of being rounded.

V2 keeps all V1 fields and their **internal-only meaning**, and adds these
fields to the closed `usermeta.cadence_contract`:

```json
{
  "expected_start": null,
  "expected_end": "2026-10-26",
  "expected_window_count": 4,
  "leading_missing_count": 0,
  "trailing_missing_count": 1,
  "boundary_missing_preview": ["2026-10-26"]
}
```

The full receipt also includes `version: 2`, `date_field`, `frequency`,
`require_complete`, `start_date`, `end_date`, `observed_count`,
`expected_count`, `missing_count`, and `missing_preview`.
A spec audit independently recomputes the exact source-bound receipt. Any
missing, malformed or stale v2 field BLOCKS; no missing values are filled.
The 10,000-period safety bound includes leading and trailing periods.

| Rule | PASS | WARN | FAIL |
| --- | --- | --- | --- |
| `data.trend.cadence.boundaries` | All explicitly expected edge slots present | Gaps when complete evidence was not required | Gaps when complete evidence was required |

### Missing-final-week CLI trap

```bash
chart-contract audit spec examples/traps/missing_trailing_week.vl.json \
  --data examples/traps/missing_trailing_week.csv \
  --claim "$(cat examples/traps/missing_trailing_week.claim.txt)"
```

Expected: `data.trend.cadence_evidence: PASS`,
`data.trend.cadence: PASS`, and
`data.trend.cadence.boundaries: FAIL` producing BLOCK.

The declaration is an operator assertion, not authentication of upstream
report completeness or data finality. The window is never inferred from
the current clock. Use the independent freshness contract for a
declared as-of data age policy.

## Grouped cadence: date × subgroup completeness (separate v1 opt-in)

The original single-series cadence v1/v2 contracts intentionally require
unique observation dates. A multi-series chart has multiple records per
date, so it uses a **separate closed**
`usermeta.group_cadence_contract`. Existing single-series receipts,
audits, and rendering remain unchanged.

```python
chart = Chart.trend(
    data=df,
    x="week", y="sales", group="channel",
    claim="Reported weekly systems across Paid and Organic.",
    source="warehouse.weekly_systems", unit="systems",
    cadence_frequency="weekly",
    cadence_require_complete=True,
    cadence_expected_groups=["Paid", "Organic"],
    cadence_expected_start="2026-10-05",  # optional
    cadence_expected_end="2026-10-19",    # optional
)
```

The first-party renderer uses the `group` field for colored series and
tooltips. External Vega-Lite specs must show a simple line with the declared
date on ordinal/temporal x, a quantitative metric on y, and the declared
subgroup on nominal/ordinal `color`. Layered and transformed views are
unsupported under this narrowly scoped grouped contract.

The operator must list every **expected** group explicitly. No missing
group can be inferred from already-observed categories. Each observed
`(date, group)` must be unique and must belong to the inventory.
Dates must be canonical `YYYY-MM-DD` and follow a daily, seven-day weekly,
or first-of-month calendar. With no expected endpoints, the common reporting
window is the minimum through maximum observed source date. With an
explicit `cadence_expected_start` and/or `cadence_expected_end`, the grid
extends only to those declared endpoints. Dates are never inferred from
the machine clock.

For five observed rows on October 5 (both groups), October 12 (both
groups) and October 19 (**Paid only**), the complete grid has 3 weeks ×
2 groups = **6 cells**. This omits **Organic on October 19**, although
every week appears somewhere in the source. The old ungrouped date check
cannot establish this type of completeness.

A first-party/externally supplied v1 receipt contains:

```json
{
  "version": 1,
  "date_field": "week",
  "group_field": "channel",
  "frequency": "weekly",
  "require_complete": true,
  "expected_groups": ["Paid", "Organic"],
  "expected_start": "2026-10-05",
  "expected_end": "2026-10-19",
  "start_date": "2026-10-05",
  "end_date": "2026-10-19",
  "observed_count": 5,
  "expected_period_count": 3,
  "expected_cell_count": 6,
  "missing_count": 1,
  "missing_preview": [
    {"date": "2026-10-19", "group": "Organic"}
  ]
}
```

The spec audit independently reconstructs the full grid from supplied
original source rows and checks **every** stored field. Reordered rows
produce identical receipts. Previews are bounded to the first five
missing cells in chronological order, then expected-group order. Grids
are capped at 10,000 group × period cells and 32 declared groups.

| Rule | PASS | WARN / REVIEW | FAIL / BLOCK |
| --- | --- | --- | --- |
| `contract.trend.cadence_groups` | Valid closed declaration and visible bindings | — | Invalid or detached group contract |
| `data.trend.cadence_groups_evidence` | Recomputed original (date, group) source receipts | — | Duplicate/off-grid/undeclared source row, malformed or stale receipts |
| `data.trend.cadence.groups` | Complete expected date × group grid | Missing cells when completeness is optional | Missing cells when complete grid required |

A strict first-party chart refuses to render when expected cells are
missing. No synthetic zero, null observation, interpolation or implicit
aggregation is ever created. A real source value of zero **is a present
observation**, not a missing subgroup-period row.

The contract is a declared completeness obligation, not proof of source
ingestion, changing group membership, business/holiday calendars, cohort
eligibility or why a subgroup was absent. Irregular/onboarding cohorts
should use a truthful, narrower inventory/window, or a different contract.
`group_cadence_contract` does not silently mix with the single-series
`cadence_contract`.

### CLI trap: one missing subgroup-week

```bash
chart-contract audit spec examples/traps/missing_subgroup_week.vl.json \
  --data examples/traps/missing_subgroup_week.csv \
  --claim "$(cat examples/traps/missing_subgroup_week.claim.txt)"
```

Expected: `contract.trend.cadence_groups: PASS` and
`data.trend.cadence_groups_evidence: PASS` (receipt matches genuine
source rows), but `data.trend.cadence.groups: FAIL`, so overall
`BLOCK`, with `Organic @ 2026-10-19` shown.

## Deliberate boundaries

- No implicit `date_range`, filling a gap with zero, interpolation, smoothing,
  or imputation. A skipped week may be a source outage or a genuinely
  non-applicable observation; the check does not infer the cause.
- No assumption that every data source has a daily/weekly/monthly cadence,
  no automatic group-level grid inference, and no support for trading-day/business-day/holiday
  calendars in v1/v2. The separate opt-in grouped contract checks only explicitly expected groups.
- An absent last week cannot be detected in v1. Declare a v2 `expected_end`
  when that date is known; use the data-freshness contract for an as-of age policy.
