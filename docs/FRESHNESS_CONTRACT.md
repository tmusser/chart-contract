# Data Freshness and Finalization Contract (v1)

A chart may have valid arithmetic, consistent scope, and convincing presentation
while silently reporting old or preliminary observations. This optional contract
makes that risk auditable **against an explicit, reproducible audit date**, without
pretending that a file's creation time or the machine clock is an authoritative
source freshness signal.

## First-party API

```python
chart = Chart.trend(
    data=frame,
    x="period", y="sales",
    claim="Recorded sales totals are shown by period.",
    source="warehouse.sales", unit="systems",
    freshness_audit_date="2026-10-29",
    freshness_observation_date_field="observation_date",
    freshness_finalized_through="2026-10-28",
    freshness_max_age_days=7,
    freshness_require_finalized=True,
)
```

The declaration is **all-or-nothing**, and available to
`Chart.trend`, `Chart.rank`, and `Chart.compare`. Omitting all five
parameters preserves legacy behavior. Declaring any one requires all five.

`freshness_audit_date` is the *as-of* date chosen by the operator.
`freshness_observation_date_field` identifies the original source column with
canonical `YYYY-MM-DD` dates, one per supplied row.
`freshness_finalized_through` is the latest date the producer declares
finalized.
`freshness_max_age_days` is an integer, nonnegative freshness policy;
`freshness_require_finalized` is a strict boolean requiring finalized evidence.

**No implicit use of today's date.** A different audit date is a different
contract. This keeps tests deterministic, lets teams audit historical dashboards,
and ensures the user chooses the age policy explicitly.

## Durable receipts

The first-party Vega-Lite renderer embeds a closed v1
`usermeta.freshness_contract` containing the five declarations, `version: 1`,
and two derived receipts:

- `data_through`: maximum canonical observation date in the *complete*
  supplied date field, not the last row or a sampled period;
- `row_count`: number of supplied source observations inspected.

Specs re-audit these receipts against supplied or otherwise reconstructable
source rows. Missing data, malformed dates, absent fields, stale receipts, empty
sources, extra contract keys, and wrong types `BLOCK`. The renderer refuses
structurally invalid declarations or unreconstructable evidence rather than
inventing receipt values.

The date field must contain canonical ISO **strings**. No coercion from arbitrary
timestamps, guessing timezone, auto-fill, date inference, or implicit row filtering.
This evidence date may differ from the plot's temporal or categorical x-axis.

## Verdict semantics

After verified receipt reconstruction:

| Rule | Condition | Outcome |
| --- | --- | --- |
| `contract.freshness.declared` | Closed v1 declaration | PASS; malformed -> FAIL |
| `data.freshness.evidence` | Source row/date receipts match | PASS; missing, malformed, or stale -> FAIL |
| `data.freshness.age` | `0 <= audit_date - data_through <= max_age_days` | PASS; future/old -> FAIL |
| `data.freshness.finalization` | `data_through <= finalized_through` | PASS |
| `data.freshness.finalization` | Preliminary data and `require_finalized=false` | WARN/REVIEW |
| `data.freshness.finalization` | Preliminary data and `require_finalized=true` | FAIL/BLOCK |

A `freshness_finalized_through` later than the audit date is invalid, since
the audit cannot rely on future finalization.

## Reproducible trap

```bash
chart-contract audit spec examples/traps/stale_sales_dashboard.vl.json \
  --data examples/traps/stale_sales_dashboard.csv \
  --claim "$(cat examples/traps/stale_sales_dashboard.claim.txt)"
```

The latest supplied sales observation is August 25, 2026, against an
October 29, 2026 audit date with `max_age_days=14`. Receipts and finalization
pass, but `data.freshness.age` fails and the chart `BLOCK`s.

## Boundaries

This verifies **the declared dates and the supplied observation evidence**.
It cannot independently prove that the source actually ingested every event,
that a declared finalized cutoff reflects a reliable source-system watermark,
that a chart needs near-real-time data, or that the operator supplied the true
current date. A finalized-but-stale dataset can still BLOCK on age; fresh but
preliminary evidence can WARN/BLOCK on finalization.

For timestamp-precision, timezone-aware freshness, dynamic wall-clock policies,
upstream watermark authentication, or reconciliation against reporting calendars,
use an explicitly designed future contract rather than hidden heuristics.
