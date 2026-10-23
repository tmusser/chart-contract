# Observation Status Contract

A numeric zero and an unavailable value are not interchangeable. A valid-looking chart can silently convert source nulls to zero and invert the business story.

Version 1 makes four explicit observation states available on descriptive trend/rank/compare evidence:

| State | Metric value required | Meaning declared |
| --- | --- | --- |
| `observed` | Finite numeric (including genuine zero) | A reported measured value |
| `structural_zero` | Exactly numeric zero | A known zero by defined structural logic |
| `missing` | Null | No available observation |
| `suppressed` | Null | An observation intentionally withheld |

Use:

```python
Chart.trend(
    data=frame,
    x="period", y="orders",
    claim="Reported orders vary by period.",
    source="warehouse.orders", unit="orders",
    observation_status_field="observation_state",
)
```

The status field must be a distinct column. No states are inferred from field names, zeros, missingness rates, geography, chart claims, or value ranges.

## Closed v1 spec receipt

A first-party Vega-Lite artifact preserves:

```json
{
  "usermeta": {
    "observation_status_contract": {
      "version": 1,
      "metric_field": "orders",
      "status_field": "observation_state",
      "counts": {
        "observed": 2,
        "structural_zero": 1,
        "missing": 0,
        "suppressed": 0
      }
    }
  }
}
```

The four counts are recomputed from original supplied rows. External spec audits require reconstructable evidence and that `metric_field` remains a displayed quantitative encoding. Malformed, missing, extra, or stale receipt fields block.

## Hero failure: zero-filled missing data

```text
period    orders    observation_state
Jan       12        observed
Feb        0        missing      <-- contradiction
Mar       14        observed
```

The numeric values would produce a visually plausible line chart. But February's value is labeled `missing`, so supplying `0` is not permitted. `data.observation.values` fails and the artifact BLOCKs. First-party rendering refuses to stamp contradictory evidence.

## Scope and limitations

- No automatic correction, filling, interpolation, or rescaling.
- Valid observed zeros remain allowed.
- `structural_zero` is a declared state only. The auditor cannot prove the upstream structural-zero logic is true.
- Nulls classified as `missing` or `suppressed` can still affect the existing evidence-coverage verdict.
- The contract records semantic state consistency; it does **not** guarantee that a given Vega-Lite mark visibly depicts gaps as a particular glyph or that viewers will recognize suppressed observations.
- No claims about MCAR/MAR/MNAR, suppression policy, nonresponse bias, or upstream ETL provenance.
- Without a status contract, the auditor does not guess whether a zero is genuine or imputed.

This is a metadata and source-evidence consistency layer, not a missing-data model.
