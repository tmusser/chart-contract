# Rank and Top-N Contract

Rank charts are easy to make visually plausible while hiding important analytical choices:

- duplicate category rows can silently become multiple bars or implicit aggregation;
- category order can drift away from metric order;
- top-N views can hide omitted categories without saying so;
- equal metric values can be split arbitrarily at the cutoff.

`chart-contract` makes those choices explicit.

## First-party API

```python
Chart.rank(
    data=df,
    x="segment",
    y="conversion_rate",
    top_n=10,
    claim="The highest observed conversion rates are concentrated in these segments.",
)
```

`top_n` is optional:

- `None` means the full eligible category set;
- a positive integer requests explicit top-N truncation;
- zero, negative, booleans, and non-integers fail `contract.rank.top_n`.

## One row per category

Rule: `data.rank.category_unique`

Rank evidence must have at most one non-null row per category.

Duplicate categories `FAIL`.

The audit never silently aggregates duplicates because sum/mean/max would each encode a
different analytical claim.

## Descending order

Rule: `visual.rank.sort_order`

First-party ranks are ordered by the quantitative metric descending.

Equal metric values are still analytically tied. The renderer uses category identity only as a
deterministic presentation order inside exact ties.

That stable order does **not** mean the tied categories have different ranks.

## Top-N and cutoff ties

Rule: `data.rank.cutoff_tie`

The top-N policy is:

```text
include_cutoff_ties
```

If `top_n=5` and categories ranked 5 and 6 have the same metric value, both are displayed.

The result therefore may contain more than N categories.

That produces `WARN / REVIEW`, not `FAIL`, because the renderer preserved the tie instead of
silently inventing a hidden tiebreak.

## Omitted-category declaration

Rule: `contract.rank.truncation`

First-party rank specs carry:

```json
{
  "usermeta": {
    "chart_contract_intent": "rank",
    "rank_contract": {
      "version": 1,
      "category_field": "segment",
      "metric_field": "conversion_rate",
      "order": "descending",
      "top_n": 5,
      "tie_policy": "include_cutoff_ties",
      "eligible_category_count": 20,
      "displayed_category_count": 5,
      "omitted_category_count": 15,
      "cutoff_tie_expanded": false
    }
  }
}
```

Counts use **eligible categories**: rows with both non-null category and metric values.

Missing analytical rows remain visible to the separate evidence-coverage rules rather than
being mislabeled as top-N omissions.

## Preserve the full source rows

First-party top-N rendering does not pre-slice the embedded dataset.

The emitted Vega-Lite artifact preserves the full supplied records and uses one bounded
category filter:

```json
{
  "transform": [
    {
      "filter": {
        "field": "segment",
        "oneOf": ["Enterprise", "Startup", "SMB"]
      }
    }
  ]
}
```

This matters because a later audit can independently reconstruct:

- the eligible category count;
- the expected displayed category set;
- the omitted category count;
- whether cutoff ties should expand the view;
- whether the filter was tampered with.

The filter is also covered by the existing transform declaration and transform-lineage receipt
contracts.

## Opt-in external rank specs

External Vega-Lite specs can opt into the rank contract with:

```json
{
  "usermeta": {
    "chart_contract_intent": "rank"
  }
}
```

Once opted in, the spec must use:

- horizontal bars;
- quantitative `x`;
- nominal/ordinal `y`;
- exact v1 `rank_contract` metadata;
- deterministic descending category sort;
- the supported bounded category `oneOf` filter when categories are omitted.

The audit compares all of those against the supplied full evidence.

## What this does not prove

A passing rank contract does not prove:

- top-N is the best presentation for the audience;
- the supplied source population is externally complete;
- category definitions are semantically correct;
- the metric itself is valid;
- omitted categories are unimportant;
- tied values are meaningfully equivalent beyond the metric shown.

The contract answers a smaller deterministic question:

**Given the supplied evidence, is the ranking unique by category, ordered correctly, explicit
about truncation, reproducible, and tie-safe?**
