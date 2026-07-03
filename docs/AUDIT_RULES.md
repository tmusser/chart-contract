# Audit Rules

Audits catch common analytical and visual-integrity failure modes. They do not prove a chart is true.

## Severity

- `PASS` means the check found the expected evidence.
- `WARN` means the chart may be shareable but needs human judgment.
- `FAIL` means the chart should not be shared without a fix.

## Rules

| Rule ID | Applies to | Severity behavior | What it checks | Suggested fix |
| --- | --- | --- | --- | --- |
| `contract.claim.present` | Chart audits and spec audits | `PASS` when a claim is declared; `FAIL` when it is missing. | Confirms the chart or spec has an explicit analytical claim. | Add a claim that states what the viewer should believe. |
| `contract.source.present` | Chart audits and spec audits | `PASS` when source is declared; `WARN` when it is missing. | Confirms provenance metadata is visible. | Add a source such as a table, model, query, or dataset identifier. |
| `data.y.column` | Chart audits | `FAIL` when the y field is absent. | Verifies the dependent metric column exists. | Add or rename the y column in the data. |
| `data.y.numeric` | Chart audits | `PASS` when y is numeric; `FAIL` when y exists but is not numeric. | Verifies the metric is quantitative. | Convert the field to numeric or choose a numeric metric. |
| `labels.unit.present` | Chart audits and spec audits | `PASS` when the quantitative metric declares a unit; `WARN` when it does not. | Checks that units are visible for quantitative values. | Add a unit such as percent, count, dollars, or rate. |
| `data.required.column` | Chart audits | `FAIL` when a required x, y, or group column is missing. | Verifies all referenced data columns exist. | Add the missing column or change the encoding to an existing field. |
| `data.not_empty` | Chart audits | `PASS` when data has rows; `WARN` when the dataset is empty. | Checks that the chart has any observations to render. | Provide data with at least one row. |
| `data.trend.min_points` | Trend chart audits | `PASS` when the trend has at least two rows; `FAIL` when it has fewer than two. | Ensures a directional trend has more than one observation. | Add historical data covering at least two time periods. |
| `data.trend.x.ordered` | Trend chart audits | `PASS` when x is ordered or datetime-like; `WARN` otherwise. | Checks that the trend axis can be read as a progression. | Use a time field, numeric sequence, or ordered categorical series. |
| `data.distribution.value.numeric` | Distribution chart audits | `PASS` when the distribution metric exists and is numeric; `FAIL` when it is missing or non-numeric. | Ensures histogram, boxplot, and violin claims use a numeric measure. | Add or convert the metric column to numeric. |
| `data.distribution.sample_size` | Distribution chart audits | `PASS` when the chart has at least 20 rows; `WARN` for 5-19; `FAIL` below 5. | Checks whether the sample is large enough to summarize shape or spread. | Collect more observations before summarizing the distribution. |
| `data.distribution.group_sample_size` | Distribution chart audits with categories | `PASS` when each non-null group has at least 10 rows; `WARN` when any group is smaller. | Checks whether grouped distributions have enough rows per category. | Aggregate small groups or collect more data for each group. |
| `readability.histogram.bins` | Histogram audits | `PASS` when bins are default/custom-controlled or an integer between 5 and 50; `WARN` when an integer falls outside that range. | Checks whether the histogram bin count stays readable. | Use a bin count between 5 and 50 unless the claim needs a custom setting. |
| `visual.violin.sample_size` | Violin audits | `PASS` when the chart has at least 30 rows; `WARN` below 30. | Checks whether a violin plot has enough rows to justify the density view. | Use a boxplot or strip/point summary when the sample is small. |
| `readability.rank.category_count` | Rank chart audits | `PASS` when categories are at or below the limit; `WARN` when there are too many. | Checks whether a rank chart stays readable. | Reduce categories or aggregate the long tail. |
| `readability.color.category_count` | Chart audits with grouped color encodings | `PASS` when group count is at or below the limit; `WARN` when there are too many. | Checks whether color encoding remains readable. | Reduce groups or facet the comparison. |
| `claim.causal_support` | Chart audits and spec audits | `PASS` when the claim is non-causal or justified; `WARN` when causal language lacks caveat/evidence. | Checks whether the claim overreaches causally. | Add a caveat or causal evidence metadata when justified. |
| `claim.event_without_caveat` | Chart audits with event annotations | `WARN` when an event is shown without a caveat; otherwise no finding. | Checks for timing-based causal inference risk. | Add a caveat clarifying whether the event is descriptive or causal. |
| `contract.filters.implied` | Chart audits | `WARN` when the claim implies a filter or time window but no filters metadata is declared; otherwise no finding. | Checks that implied scope is explicit. | Add filters metadata or clarify the time window in the contract. |
| `labels.title.quality` | Chart audits and spec audits | `PASS` when the title is specific; `WARN` when it is missing or generic. | Checks whether the title supports interpretation. | Use a specific title or a concrete analytical claim. |
| `visual.intent.match` | Chart audits | `PASS` when the visual form matches the declared chart intent. | Checks that the chosen mark fits the intent. | Choose a visual form that matches the intended comparison. |
| `visual.integrity.decoration` | Chart audits and spec audits | `PASS` when no decorative/chartjunk-like terms are detected; `WARN` when decorative terms appear in chart audits or non-arc spec audits; `FAIL` when decorative terms appear in an arc spec audit. | Checks for chartjunk-like or depth-like metadata. | Remove decorative fields and prefer plain analytical encodings. |
| `scale.bar.nonzero_baseline` | Spec audits for bar marks | `PASS` when a bar chart keeps a zero baseline; `FAIL` when it disables zero on a quantitative axis. | Checks for misleading bar length comparisons. | Set `scale.zero = true` on quantitative bar axes. |
| `visual.arc.category_count` | Spec audits for arc marks | `PASS` when an arc chart stays at or below the category limit; `FAIL` when it exceeds the limit. | Checks whether a pie/arc chart uses too many categories. | Switch to a sorted bar chart. |

## How to add a new rule

- Choose a stable `rule_id`.
- Write a clear message.
- Include a suggestion when possible.
- Add or update tests.
- Document the rule here.

## Known limits

- Audits cannot prove causality.
- Audits cannot detect all misleading framing.
- Audits cannot replace domain review.
- Audits depend on metadata quality.
