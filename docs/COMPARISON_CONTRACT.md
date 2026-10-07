# Comparison Baseline Contract

Comparative claims are incomplete unless the reference point and change arithmetic are explicit.

`chart-contract` version 1 supports baseline contracts for:

- `Chart.trend()`
- `Chart.compare()`

It distinguishes four change types:

- `absolute`
- `percentage_points`
- `percent_change`
- `ratio`

## First-party API

```python
chart = Chart.trend(
    data=df,
    x="year",
    y="revenue",
    claim="Revenue increased by 20%.",
    source="warehouse.revenue",
    unit="dollars",
    baseline_field="year",
    baseline_value="2025",
    target_value="2026",
    change_type="percent_change",
    declared_change=20.0,
)
```

The baseline field must be a visible comparison dimension in v1:

- `x`, or
- `group`.

Each selector must resolve to exactly one source row.

## Change semantics

For baseline `b` and target `t`:

```text
absolute          = t - b
percent_change    = ((t - b) / b) * 100
ratio             = t / b
percentage_points = percent-scale difference
```

`percent_change` and `ratio` are undefined when the baseline is zero.

Percentage-point change requires explicit percent source semantics:

- `unit="percent"` / `"percentage"` / `"%"`;
- `value_representation="fraction"` or `"percentage_points"`.

If the source representation is fractional, `0.40 -> 0.45` is a 5 percentage-point change.

If the source representation is percentage points, `40 -> 45` is also a 5 percentage-point change.

## Durable receipts

First-party specs preserve:

```json
{
  "usermeta": {
    "comparison_contract": {
      "version": 1,
      "metric_field": "revenue",
      "baseline_field": "year",
      "baseline_value": "2025",
      "target_value": "2026",
      "change_type": "percent_change",
      "declared_change": 20.0,
      "baseline_metric_value": 100.0,
      "target_metric_value": 120.0,
      "computed_change": 20.0
    }
  }
}
```

The observed metric values and computed change are receipts, not user-editable justification.
A later spec audit recomputes them from the supplied evidence.

Stale receipt values or a wrong declared change block.

## Claim-language parity

Rule: `claim.comparison.change_semantics`

The claim parser is intentionally narrow. It recognizes explicit numeric phrases such as:

- `20%` / `20 percent` -> percent change
- `5 percentage points` / `5 pp` -> percentage-point change
- `2x` / `2×` / `2 times` -> ratio

For explicit percent-valued metrics, `5 points` is also interpreted as percentage points.

This catches a common semantic error:

```text
40% -> 60%
```

is:

- **+20 percentage points**
- **+50% relative change**

It is not “up 20%.”

General prose such as “improved versus last year” is not parsed into a change type. The
contract still verifies its declared arithmetic, but chart-contract does not pretend to solve
open-ended natural-language semantics.

## Missing baseline metadata

If a claim contains a narrow explicit numeric comparison phrase but no comparison contract,
`contract.comparison.baseline` produces `WARN / REVIEW`.

Missing metadata is therefore reviewable; contradictory declared arithmetic is a deterministic
`FAIL / BLOCK`.

## External specs

External Vega-Lite specs may carry the same closed version-1
`usermeta.comparison_contract`.

A passing audit requires:

- the metric field is a visible quantitative encoding;
- the baseline field is visibly encoded;
- supplied evidence is available;
- baseline and target selectors each resolve to one row;
- stored metric/change receipts match recomputation;
- the declared change matches recomputation;
- any recognized explicit numeric claim language matches the contract.

## Boundaries

A passing comparison contract does not prove:

- the chosen baseline is analytically appropriate;
- the two observations are causally comparable;
- seasonality or cohort composition is controlled;
- the metric itself is valid;
- rounding in arbitrary display prose is correct unless the explicit numeric phrase matches
  the contract exactly.

Version 1 answers a narrower question:

**Which observations were compared, what arithmetic was declared, does that arithmetic
recompute from the supplied evidence, and does explicit numeric claim language use the same
change semantics?**
