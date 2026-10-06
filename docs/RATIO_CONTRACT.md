# Ratio Denominator and Cohort Contract

Rates, ratios, conversion metrics, and percentages are incomplete without knowing what they
are "of."

A value such as `0.20` can mean very different things depending on whether the denominator is:

- all visitors;
- signed-in visitors;
- started checkouts;
- eligible accounts;
- submitted applications.

`chart-contract` makes that denominator identity explicit without pretending to reconstruct
upstream business logic.

## First-party API

Version 1 applies to the first-party metric-comparison intents:

- `Chart.trend()`
- `Chart.rank()`
- `Chart.compare()`

Example:

```python
chart = Chart.compare(
    data=df,
    x="segment",
    y="conversion_rate",
    claim="Enterprise has the higher observed conversion rate.",
    source="warehouse.funnel_summary",
    unit="conversion rate",
    numerator="converted_users",
    denominator="eligible_sessions",
    cohort="sessions eligible for the onboarding funnel",
)
```

The required semantic identities are:

- `numerator`
- `denominator`

Optional fields are:

- `cohort`: a human-readable identity for the denominator population;
- `denominator_basis_field`: a source-data field whose row values must all equal the declared
  denominator identity.

## Missing semantics

Rule: `contract.ratio.denominator`

Ratio-like units include:

- percent / percentage / `%`;
- `rate`;
- `ratio`;
- units ending in ` rate` or ` ratio`, such as `conversion rate` or `win rate`.

A ratio-like metric with no ratio contract produces `WARN / REVIEW`.

That is deliberately different from a contradictory contract, which `FAIL / BLOCK`s.

The audit never guesses numerator or denominator identity from:

- the metric field name;
- observed value ranges;
- claim text;
- upstream table names.

## Closed version-1 spec metadata

First-party specs preserve:

```json
{
  "usermeta": {
    "ratio_contract": {
      "version": 1,
      "metric_field": "conversion_rate",
      "numerator": "converted_users",
      "denominator": "eligible_sessions",
      "cohort": "sessions eligible for the onboarding funnel",
      "denominator_basis_field": null
    }
  }
}
```

External specs may use the same exact schema.

The contract is closed: missing or extra fields, unsupported versions, blank semantic
identities, and metric-field drift block.

A declared ratio contract may also be used with a nonstandard unit such as
`events per thousand sessions`; explicit metadata is stronger evidence than a unit-name
heuristic.

## Row-level denominator identity

Rule: `data.ratio.denominator_basis`

When `denominator_basis_field` is declared, every supplied row must contain a non-empty
string identity and all rows must agree with the contract's `denominator`.

Example evidence:

```text
segment       conversion_rate   denominator_basis
SMB           0.10              visitors
Enterprise    0.20              signups
```

A chart labeling both rows as one `conversion rate` while declaring
`denominator="visitors"` will block because the comparison mixes denominator meanings.

This is semantic identity, not numeric denominator size. Different rows may legitimately have
different visitor counts; they must still mean the same kind of denominator.

## Cohort identity

`cohort` is optional descriptive metadata for the population definition.

Examples:

- `all observed funnel traffic`
- `eligible onboarding sessions`
- `active paid accounts at period start`

Version 1 preserves cohort identity but does not attempt to parse prose or prove every source
row actually belongs to that cohort.

Existing `filters` metadata remains the place for explicit chart filter/window declarations.

## Percent semantics remain separate

The denominator contract does not replace `value_representation`.

For a percentage metric, both questions matter:

1. Does raw `0.42` mean 42%, or does raw `42` mean 42%?
2. 42% of **what**?

Example:

```python
Chart.trend(
    ...,
    unit="percent",
    value_representation="fraction",
    numerator="converted_sessions",
    denominator="eligible_sessions",
)
```

The percent contract handles display scaling.

The ratio contract handles numerator/denominator meaning.

Neither silently rescales or recomputes the source metric.

## What this does not prove

A passing ratio contract does not prove:

- the displayed metric equals numerator divided by denominator;
- upstream SQL calculated the rate correctly;
- the source denominator population is complete;
- every row truly belongs to the declared cohort;
- the numerator and denominator are scientifically appropriate;
- a ratio is the right statistic for the claim.

Version 1 answers a narrower question:

**Is the numerator/denominator meaning explicit, bound to the shown metric, and—when a
row-level denominator identity field is supplied—consistent across the evidence?**
