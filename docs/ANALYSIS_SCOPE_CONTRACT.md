# Analysis Scope Contract

A stable metric name does not guarantee a stable analytical universe.

Examples of scope drift include:

- US paid customers in one period and all customers in another;
- production traffic mixed with internal/test traffic;
- enterprise accounts mixed with all account tiers;
- one cohort version silently replacing another while the metric field stays unchanged.

`chart-contract` makes that filtered/cohort universe identity explicit without executing arbitrary filter logic.

## First-party API

```python
Chart.trend(
    ...,
    scope_id="us_paid_customers",
    scope_definition="Users with country=US and billing_status=paid.",
    scope_version="v1",
    scope_basis_field="analysis_scope",
    scope_basis_value="us_paid_v1",
)
```

## Closed version-1 metadata

```json
{
  "usermeta": {
    "analysis_scope_contract": {
      "version": 1,
      "scope_id": "us_paid_customers",
      "scope_definition": "Users with country=US and billing_status=paid.",
      "scope_version": "v1",
      "scope_basis_field": "analysis_scope",
      "scope_basis_value": "us_paid_v1"
    }
  }
}
```

The schema is closed.

If any scope identity is declared, `scope_id`, `scope_definition`, and `scope_version`
are required together.

The optional `scope_basis_field` and `scope_basis_value` must be declared together.

## Row-level scope identity

When a row-level basis is declared:

- the basis field must exist;
- values must be non-null, non-empty strings;
- all supplied rows must carry one common scope identity;
- that identity must exactly match `scope_basis_value`.

Mixed values such as:

```text
us_paid_v1
all_customers_v1
```

block instead of being treated as comparable evidence.

## Relationship to filters

The existing `filters` metadata remains presentation/provenance text.

Version 1 does not parse or execute arbitrary SQL predicates, Vega expressions, dbt logic, or
free-form filter strings merely to make a scope contract pass.

A scope definition can document the intended universe, while the optional basis field provides
bounded row-level identity evidence.

## What version 1 does not prove

A passing scope contract does **not** prove:

- the declared scope is analytically appropriate;
- upstream SQL or Python implemented the filter correctly;
- cohort membership is complete;
- the scope definition is semantically equivalent to another definition;
- excluded entities should have been excluded;
- filter predicates were applied before aggregation;
- external data sources used the same scope merely because they reuse the same label.

It proves only that the artifact declares one scope identity/version and, when row-level basis
evidence is supplied, that the supplied rows consistently carry that declared identity.
