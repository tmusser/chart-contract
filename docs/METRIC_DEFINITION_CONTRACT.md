# Metric Definition Identity Contract

A quantitative field can keep the same column name while its business definition changes.

Examples:

- `active_users` moves from trailing-30-day activity to trailing-7-day activity;
- `revenue` changes from gross to net;
- `conversion` changes eligibility rules;
- `churn` changes cancellation or grace-period logic.

A chart can remain numerically well-formed while comparing different metric concepts.

Version 1 makes metric identity explicit for:

- `Chart.trend()`
- `Chart.rank()`
- `Chart.compare()`

## First-party API

```python
chart = Chart.trend(
    data=df,
    x="period",
    y="active_users",
    claim="Observed active users changed.",
    source="warehouse.product_metrics",
    unit="users",
    metric_id="monthly_active_users",
    metric_definition="Unique users with at least one qualifying session in the measurement window.",
    metric_version="v3",
    metric_basis_field="metric_version",
)
```

The required semantic identity is:

- `metric_id`
- `metric_definition`
- `metric_version`

`metric_basis_field` is optional.

If any metric-definition metadata is declared, the required fields must all be present and
non-empty.

## Closed spec metadata

First-party specs preserve:

```json
{
  "usermeta": {
    "metric_definition_contract": {
      "version": 1,
      "metric_field": "active_users",
      "metric_id": "monthly_active_users",
      "metric_definition": "Unique users with at least one qualifying session in the measurement window.",
      "metric_version": "v3",
      "metric_basis_field": "metric_version"
    }
  }
}
```

The contract must bind to a quantitative field shown by the chart/spec.

## Row-level definition version

When `metric_basis_field` is declared, every supplied row must contain:

- a non-null value;
- a non-empty string;
- one common version identity;
- a value exactly matching `metric_version`.

So this blocks:

```text
period    active_users    metric_version
before    100             v1
after     120             v2
```

even though `active_users` has the same field name in both rows.

Rule: `data.metric.definition_basis`.

## Opt-in boundary

Version 1 does not infer metric identity from:

- the field name;
- the chart title;
- the claim;
- source names;
- units;
- observed values.

A chart with no metric-definition contract is not automatically downgraded.

That keeps this contract usable where a metric catalog/version is actually available instead
of forcing callers to invent false metadata.

Once declared, however, partial, malformed, mismatched, or mixed metric identity blocks.

## What this does not prove

A passing metric-definition contract does not prove:

- the business definition is sensible;
- upstream SQL/Python actually implemented the declared definition;
- the versioning scheme is trustworthy;
- two different version strings necessarily imply a material analytical difference;
- the metric is scientifically or operationally valid.

It answers a smaller deterministic question:

**Did the artifact declare one metric concept/version, bind it to the shown field, and—when
row-level evidence is available—use that same declared version throughout the supplied
evidence?**
