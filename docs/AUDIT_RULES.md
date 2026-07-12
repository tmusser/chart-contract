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
| `data.encoding.fields` | Spec audits with data | `PASS` when every encoded field exists; `FAIL` when any encoded field is absent. | Verifies object and shorthand Vega-Lite encodings reference real columns. | Add the missing columns or update the encodings. |
| `data.encoding.quantitative` | Spec audits with data | `PASS` when quantitative encoded fields are numeric; `FAIL` when any are non-numeric. | Verifies `quantitative` / `:Q` encodings match the supplied data. | Convert the fields to numeric or change their encoding type. |
| `data.not_empty` | Chart audits | `PASS` when data has rows; `WARN` when the dataset is empty. | Checks that the chart has any observations to render. | Provide data with at least one row. |
| `data.trend.min_points` | Trend chart and line-spec audits | `PASS` with at least two complete x/y observations; `FAIL` with fewer than two. | Ensures a directional trend has more than one usable observation. | Add at least two observations with non-null x and y values. |
| `data.trend.x.ordered` | Trend chart audits | `PASS` when x is ordered or datetime-like; `WARN` otherwise. | Checks that the trend axis can be read as a progression. | Use a time field, numeric sequence, or ordered categorical series. |
| `data.distribution.value.numeric` | Histogram, boxplot, violin, QQ, and ECDF audits | `PASS` when the distribution metric exists and is numeric; `FAIL` when it is missing or non-numeric. | Ensures distribution and quantile diagnostics use a numeric measure. | Add or convert the metric column to numeric. |
| `data.distribution.sample_size` | Distribution and quantile chart audits | `PASS` with at least 20 non-null numeric metric observations; `WARN` for 5-19; `FAIL` below 5. | Checks whether the usable sample is large enough to summarize shape or quantiles. | Collect more valid observations before interpreting the distribution. |
| `data.distribution.group_sample_size` | Grouped distribution and quantile chart audits | `PASS` when each non-null group has at least 10 valid metric rows; `WARN` when any group is smaller. | Checks whether grouped distributions have enough usable rows per category. | Aggregate small groups or collect more data for each group. |
| `readability.histogram.bins` | Histogram audits | `PASS` when bins are default/custom-controlled or an integer between 5 and 50; `WARN` when an integer falls outside that range. | Checks whether the histogram bin count stays readable. | Use a bin count between 5 and 50 unless the claim needs a custom setting. |
| `visual.violin.sample_size` | Violin audits | `PASS` when the chart has at least 30 valid metric observations; `WARN` below 30. | Checks whether a violin plot has enough usable rows to justify the density view. | Use a boxplot or strip/point summary when the sample is small. |
| `stat.qq.reference_distribution` | QQ audits | `PASS` for the implemented normal reference; `FAIL` for unsupported references. | Prevents a QQ label from implying a distribution whose quantiles are not implemented. | Use `distribution="normal"` until another reference is explicitly supported. |
| `stat.qq.tie_density` | QQ audits | `WARN` when fewer than half of 10+ observations are distinct; otherwise `PASS`. | Flags rounded or discrete samples whose ties can obscure tail behavior. | Interpret cautiously or use an ECDF for discrete data. |
| `data.residual.fitted.numeric` | Residual audits | `PASS` when fitted values are numeric; `FAIL` otherwise. | Ensures the residual x-axis represents a quantitative fitted value. | Provide the numeric model prediction column. |
| `data.residual.sample_size` | Residual audits | `PASS` with at least 20 complete fitted/residual pairs; `WARN` for 5-19; `FAIL` below 5. | Checks whether pattern judgments have enough complete observations. | Provide more fitted/residual pairs before interpreting structure. |
| `data.residual.variation` | Residual audits | `WARN` when residuals have no variation; otherwise `PASS`. | Detects suspiciously constant residual exports. | Verify the prediction and residual calculation pipeline. |
| `visual.residual.zero_reference` | Residual audits | `PASS` for the first-party renderer. | Confirms the diagnostic includes a zero reference line. | Use the first-party residual renderer or add an explicit zero line. |
| `readability.rank.category_count` | Rank chart audits | `PASS` when categories are at or below the limit; `WARN` when there are too many. | Checks whether a rank chart stays readable. | Reduce categories or aggregate the long tail. |
| `readability.color.category_count` | Chart audits with grouped color encodings | `PASS` when group count is at or below the limit; `WARN` when there are too many. | Checks whether color encoding remains readable. | Reduce groups or facet the comparison. |
| `claim.causal_support` | Chart audits and spec audits | `PASS` when the claim is non-causal or justified; `WARN` when causal language lacks caveat/evidence. | Checks whether the claim overreaches causally. | Add a caveat or causal evidence metadata when justified. |
| `claim.event_without_caveat` | Chart audits with event annotations | `WARN` when an event is shown without a caveat; otherwise no finding. | Checks for timing-based causal inference risk. | Add a caveat clarifying whether the event is descriptive or causal. |
| `contract.filters.implied` | Chart audits | `WARN` when the claim implies a filter or time window but no filters metadata is declared; otherwise no finding. | Checks that implied scope is explicit. | Add filters metadata or clarify the time window in the contract. |
| `labels.title.quality` | Chart audits and spec audits | `PASS` when the title is specific; `WARN` when it is missing or generic. | Checks whether the title supports interpretation. | Use a specific title or a concrete analytical claim. |
| `visual.intent.match` | Chart audits | `PASS` for supported intents; `FAIL` for unsupported direct intent values. | Prevents audit success for a chart that the renderer cannot render. | Use one of the supported `Chart` constructors. |
| `visual.integrity.decoration` | Chart audits and spec audits | `PASS` when no decorative/chartjunk-like terms are detected; `WARN` when visual metadata contains them in chart or non-arc spec audits; `FAIL` for arc specs. | Checks visual configuration without treating data values, dataset hashes, or provenance text as decoration. | Remove decorative visual fields and prefer plain analytical encodings. |
| `scale.bar.nonzero_baseline` | Spec audits for bar marks | `PASS` when a bar chart keeps a zero baseline; `FAIL` when it disables zero on a quantitative axis. | Checks for misleading bar length comparisons. | Set `scale.zero = true` on quantitative bar axes. |
| `visual.arc.category_count` | Spec audits for arc marks | `PASS` when an arc chart stays at or below the category limit; `FAIL` when it exceeds the limit. | Checks whether a pie/arc chart uses too many categories, including shorthand encodings. | Switch to a sorted bar chart. |

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
- Statistical diagnostic audits validate data and rendering contracts; they do not perform hypothesis tests or certify model adequacy.
- Layered spec audits inspect the first supported analytical layer; complex multi-view composition remains experimental.
