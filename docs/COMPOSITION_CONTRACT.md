# Subgroup Composition Reversal Contract

An aggregate rate can move opposite to **every constituent subgroup's rate** when
subgroup denominator weights change (a Simpson-type reversal). A numerically
correct overall rate is therefore not sufficient evidence for an intuitive
"everyone improved/declined" interpretation.

## Opt-in first-party API

Use a **grouped `Chart.compare`**, with one row for each subgroup and
each named period. Supply the existing v2 ratio numeric evidence fields.

```python
Chart.compare(
    data=frame,
    x="period", group="cohort", y="conversion_rate",
    claim="The observed conversion rates changed by cohort.",
    source="synthetic.funnel", unit="conversion rate",
    numerator="conversions", denominator="sessions",
    numerator_value_field="conversions",
    denominator_value_field="sessions",
    composition_baseline_value="before",
    composition_target_value="after",
)
```

A declaration is optional. Supplying either composition period opts into a
closed v1 `usermeta.composition_contract` requiring both values, and binds:

- visible `period_field`, `group_field`, `metric_field`;
- numeric numerator/denominator fields, `multiplier`, `tolerance`;
- exact baseline and target period values;
- recomputed baseline/target numerator/denominator totals and weighted rates;
- matched subgroup count and within-group/aggregate direction receipts;
- `reversal`: whether all subgroups move strictly together against the aggregate.

The first-party renderer stamps exact numeric receipts and **refuses to render**
inconsistent or incomplete source data. External spec audits recompute all
receipts from independently supplied or reconstructable data, failing stale
metadata and detached visible fields.

## Example: mathematically correct but counterintuitive

| Cohort | Before successes/total | After successes/total |
| --- | --- | --- |
| High | 80/100 = 80% | 9/10 = 90% |
| Low | 2/10 = 20% | 30/100 = 30% |
| Weighted overall | 82/110 = 74.55% | 39/110 = 35.45% |

**Both groups rise, yet the overall rate falls.**

A verified reversal triggers `data.composition.reversal -> WARN / REVIEW`,
not a FAIL: the data are arithmetically consistent but potentially easy to
misinterpret. No reversal returns PASS, not a claim that confounding is absent.

The accompanying CLI trap is `simpsons_paradox_conversion`.

## Strict reconstruction and gates

- `contract.composition.declared`: closed metadata and visible encoding bindings.
- `data.composition.evidence`: strict source evidence and receipt parity.
- `data.composition.reversal`: purely directional subgroup-vs-overall warning.

Version 1 deliberately supports **exactly two declared periods** and **two or more
matched subgroups**. Each period/subgroup combination must appear exactly once.
No extra periods, silent grouping, dropped subgroups, empty keys, or join-fanout
repair. Numeric data must be finite, counts nonnegative with positive denominators,
and the numerator cannot exceed the denominator (bounded proportion semantics).
Displayed subgroup rates must reproduce supplied numerator/denominator arithmetic
within the explicitly declared absolute tolerance. Aggregates are recomputed
from sums of counts, **never an unweighted mean of subgroup rates**.

For v1, identical subgroup labels imply matched grouping categories, not proven
stable cohort membership. A passing composition check cannot prove that
population exclusions, source data, group definitions, upstream joins,
or business meaning are correct.

## Boundaries

No SQL execution, causal claims, statistical significance, automatic weight
normalization, or assumption that a reversal establishes confounding.
A chart with changing subgroups must choose a different audit contract rather
than hiding those changes to make this one pass. This feature complements
`analysis_scope_contract`, ratio v2 arithmetic, and time-window checks.
