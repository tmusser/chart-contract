# Evidence Coverage and Missingness

A chart can render from a small complete subset while the source evidence contains many rows
with missing analytical fields.

`chart-contract` makes that loss visible before sharing.

## Usable-row coverage

For a chart or auditable Vega-Lite spec, evidence coverage is:

```text
usable rows / source rows
```

A row is usable when every field required for the visible analytical evidence is non-null.

Current deterministic thresholds:

- **PASS**: at least 90% usable rows
- **WARN / REVIEW**: at least 50% but below 90%
- **FAIL / BLOCK**: below 50%

Example:

```text
Spec evidence uses 812 / 1041 rows (78.0%) complete across week, conversion_rate.
```

The rule ID is `data.coverage.usable_rows`.

The thresholds are guardrails, not statistical missing-data theory. They make substantial
row loss explicit without guessing why values are missing.

## Which fields count

For first-party chart audits, coverage uses the fields required by the chart contract:
x/value/y plus explicit grouping fields when applicable.

For external Vega-Lite specs, coverage uses visible analytical encoding channels:

- `x`
- `y`
- `color`
- `theta`
- `radius`
- `row`
- `column`
- `detail`
- `size`
- `shape`

Tooltip-only fields do not reduce coverage because a null tooltip does not remove the primary
mark from the evidence being shown.

If a required encoded field is completely absent from supplied data, the existing
`data.encoding.fields` rule handles that failure. The coverage rule does not emit a second
derived percentage from an incomplete field contract.

## Grouped coverage

When the chart has an auditable comparison group, chart-contract also checks whether
complete-case coverage is materially uneven across groups.

The rule ID is `data.coverage.group_balance`.

To avoid tiny-denominator noise, only groups with at least five source rows participate.
At least two eligible groups are required.

Current threshold:

- gap below 20 percentage points -> **PASS**
- gap of 20 percentage points or more -> **WARN / REVIEW**

Example:

```text
Grouped usable-row coverage spans 80.0%-100.0% across 2 groups in 'segment' (20.0% gap).
```

The finding deliberately reports the range rather than group values. The purpose is to surface
uneven evidence retention without leaking category labels into a portable audit message.

## What this does not prove

A passing coverage result does not prove:

- missingness is random;
- retained rows are representative;
- source data are unbiased;
- measurement is correct;
- groups are comparable;
- a claim is statistically supported.

A warning does not prove that missingness caused bias either.

The rules answer a smaller deterministic question:

**How much of the supplied source evidence is complete enough to support the visible chart
fields, and is that retention conspicuously uneven across comparison groups?**

## Transform boundary

Coverage does not execute arbitrary Vega-Lite transforms.

If an encoded field exists only after a `calculate`, `window`, lookup, or another transform
that chart-contract cannot deterministically reconstruct from the supplied evidence, existing
field-contract rules remain authoritative and coverage is not fabricated from guessed output.

Transform transparency and evidence coverage are complementary:

- transform auditing asks what the spec says it changes;
- coverage auditing asks how much supplied evidence is complete for visible fields.

Neither substitutes for domain review.
