# Population and Sampling Contract

A chart can be internally consistent while the supplied evidence represents only a sample of a larger population.

`chart-contract` makes that scope explicit without claiming that a sampling design is statistically valid or representative.

## First-party API

```python
Chart.trend(
    ...,
    evidence_scope="sample",
    population="All eligible product users",
    population_size=100000,
    sample_size=2500,
    sampling_method="stratified",
    sample_member_field="user_id",
    weight_field="survey_weight",
    generalizes_to_population=True,
)
```

Version 1 supports:

- `evidence_scope="sample" | "census"`
- explicit population identity
- declared population size when known
- declared sample size
- a bounded sampling-method vocabulary
- optional row-level sample-member identity
- optional row-level positive weights
- explicit population-generalization intent

## Sample versus census

For `sample` evidence:

- `sampling_method` cannot be `census`;
- `sample_size` must be positive;
- when `population_size` is declared, `sample_size < population_size`.

For `census` evidence:

- `sampling_method="census"`;
- `population_size` is required;
- `sample_size == population_size`;
- v1 does not accept a sampling `weight_field`.

## Declared sample size is not DataFrame row count

Analytical charts are often aggregated.

A chart with 12 monthly rows may summarize a sample of 25,000 people. Therefore chart-contract does **not** equate row count with `sample_size`.

When `sample_member_field` is omitted, sample size remains explicit declarative metadata.

When `sample_member_field` is supplied, the audit requires:

- the field to exist;
- no null or blank IDs;
- one unique ID per supplied row;
- the reconstructed unique count to exactly equal `sample_size`.

This path is only appropriate when the supplied evidence is actually one row per sampled unit.

## Sampling methods

Version 1 accepts:

- `census`
- `simple_random`
- `stratified`
- `systematic`
- `cluster`
- `convenience`
- `quota`
- `unknown`
- `other`

These names are semantic declarations, not proof that the sampling procedure was executed as labeled.

## Weights

When `weight_field` is declared, every supplied weight must be:

- present;
- numeric;
- finite;
- strictly positive.

A passing weight check does not prove:

- calibration targets are correct;
- inverse-probability weights are correctly derived;
- post-stratification is appropriate;
- uncertainty estimates account for the design;
- weighted estimates are unbiased.

## Population generalization

`generalizes_to_population` is explicit metadata. The audit does not attempt broad natural-language inference from arbitrary claim text.

If generalization is false, the artifact is treated as descriptive of the observed evidence.

If generalization is true:

- census evidence passes the structural check;
- probability-method declarations pass the structural check;
- `convenience`, `quota`, `unknown`, or `other` sampling produces `REVIEW`.

This is a deterministic review signal, not a statistical theorem. A declared simple-random or stratified sample can still be biased in practice.

## Closed version-1 metadata

```json
{
  "usermeta": {
    "population_contract": {
      "version": 1,
      "evidence_scope": "sample",
      "population": "All eligible product users",
      "population_size": 100000,
      "sample_size": 2500,
      "sampling_method": "stratified",
      "sample_member_field": "user_id",
      "weight_field": "survey_weight",
      "generalizes_to_population": true
    }
  }
}
```

The schema is closed. Partial or contradictory contracts block.

## What version 1 does not prove

A passing contract does **not** prove:

- the declared target population is the right population;
- the sampling frame covered that population;
- selection probabilities were implemented correctly;
- nonresponse is ignorable;
- weights are calibrated correctly;
- the observed sample is representative;
- population generalization is statistically justified;
- design effects or uncertainty are correctly estimated.

It proves only that population/sampling semantics are explicit and internally consistent against any row-level member or weight evidence supplied to the audit.
