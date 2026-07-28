# Set Membership Charts

`Chart.set_membership()` is a first-class two-set analytical intent for claims about membership, overlap, exclusion, and coverage.

It produces a Venn-style view, but the contract is deliberately stricter than “draw two circles.” The input must preserve row-level membership evidence, the audit must reconcile all four regions, and the rendered geometry is explicitly schematic rather than area-proportional.

## Data contract

Use one row per member of the declared universe:

| customer_id | email | paid_search |
| --- | ---: | ---: |
| c1 | 1 | 0 |
| c2 | 1 | 1 |
| c3 | 0 | 1 |
| c4 | 0 | 0 |

Membership columns must contain only non-null booleans or integer `0`/`1` values. Member identifiers must be non-null and unique so duplicate rows cannot silently inflate a region.

## Python API

```python
import pandas as pd
from chart_contract import Chart

frame = pd.DataFrame(
    {
        "customer_id": ["c1", "c2", "c3", "c4"],
        "email": [1, 1, 0, 0],
        "paid_search": [0, 1, 1, 0],
    }
)

chart = Chart.set_membership(
    data=frame,
    member="customer_id",
    set_a="email",
    set_b="paid_search",
    set_a_label="Email",
    set_b_label="Paid search",
    claim="Email and paid search overlap for one of four customers.",
    source="warehouse.channel_reach",
    title="Customer reach overlap by channel",
)

report = chart.audit()
spec = chart.to_vega_lite()
```

The generated spec stores the reconciled region counts and the schematic-area declaration in `usermeta.set_membership`.

## Audit boundary

The first-party audit checks:

- the member and two set columns exist;
- membership values are explicit booleans or `0`/`1` integers;
- member identifiers are non-null and unique;
- A-only, overlap, B-only, and neither counts reconcile to the universe;
- provenance, claim, title, caveat, filters, and visual-integrity rules remain active;
- the renderer declares that labeled region counts—not circle area—are authoritative.

A valid chart can be `READY`. Invalid membership evidence or duplicate members produce `BLOCK`.

## Supported relationships

The renderer handles partial overlap, disjoint sets, subset relationships, and equal sets with different schematic layouts. Region labels carry the actual evidence in every case.

## Intentional limits

This slice supports exactly two unweighted sets. It does not support:

- three-or-more-set Venn diagrams;
- probabilistic or fuzzy membership;
- weighted members;
- area-proportional circle fitting;
- automatic conversion to UpSet or Euler diagrams;
- reconstructing row-level membership evidence from an arbitrary Vega-Lite spec.

For more than two sets, a matrix or UpSet-style view is usually more auditable than adding more circles. That is a separate future intent, not an automatic fallback.
