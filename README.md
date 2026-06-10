# chart-contract

A lightweight Python harness for claim-first, audited analytical charts.

Charts should satisfy analytical contracts, not just render.

`chart-contract` helps analysts and AI agents produce claim-first charts that can be audited before sharing. A chart should not just render; it should declare what it claims, what data supports it, and what could mislead the reader. Charts are reasoning artifacts, not decorations.

## Why This Matters

AI-generated charts can look plausible while hiding weak claims, missing units, missing sources, misleading visual forms, or causal overreach. `chart-contract` makes those assumptions explicit before the chart is shared.

It is a chart-contract harness:

`claim -> data contract -> visual choice -> audit -> render`

It is intentionally not a full visualization library, not a dashboard tool, and not an AI chart generator.

## Bad Chart -> Audit -> Corrected Chart

The repo leads with a risky chart example because that is the point of the package: catch weak analytical defaults before a chart gets shared.

```python
import pandas as pd
from chart_contract import Chart, audit_spec

df = pd.DataFrame(
    {
        "segment": ["SMB", "Enterprise", "Mid-Market", "Public", "Startup", "Partners", "Other"],
        "conversion_rate": [0.09, 0.18, 0.14, 0.12, 0.16, 0.11, 0.08],
    }
)

bad_vega_lite_spec = {
    "mark": {"type": "arc", "innerRadius": 40},
    "title": "Chart",
    "encoding": {
        "theta": {"field": "conversion_rate", "type": "quantitative"},
        "color": {"field": "segment", "type": "nominal"},
    },
}

findings = audit_spec(
    spec=bad_vega_lite_spec,
    data=df,
    claim="The onboarding launch caused conversion lift across customer segments.",
)

corrected = Chart.rank(
    data=df.sort_values("conversion_rate", ascending=False),
    x="segment",
    y="conversion_rate",
    claim="Enterprise and startup segments show the highest observed conversion rates.",
    source="synthetic.segment_conversion",
    unit="conversion rate",
    caveat="Observational segment summary; not causal proof for the onboarding launch.",
)
```

Representative audit output from `python examples/bad_to_good_chart.py`:

```text
PASS contract.claim.present
WARN contract.source.present
WARN labels.title.quality
WARN claim.causal_support
FAIL visual.arc.category_count
PASS readability.color.category_count
```

Run the full hero demo with:

```bash
python examples/bad_to_good_chart.py
```

It audits the risky pie-like chart, prints PASS/WARN/FAIL findings, and writes a corrected Vega-Lite spec to [examples/output/corrected_chart.vl.json](examples/output/corrected_chart.vl.json).

Outputs from the hero demo:

- [Corrected Vega-Lite spec](examples/output/corrected_chart.vl.json)
- [Audit report, Markdown](examples/output/bad_chart_audit.md)
- [Audit report, JSON](examples/output/bad_chart_audit.json)
- [Bad chart SVG](examples/output/bad_chart.svg)
- [Corrected chart SVG](examples/output/corrected_chart.svg)

The hero demo now commits lightweight rendered charts alongside the audit artifacts so the first impression is inspectable without extra tooling.

## Quickstart

```bash
python -m pip install -e ".[dev]"
python examples/bad_to_good_chart.py
pytest
```

## API

```python
import pandas as pd
from chart_contract import Chart

df = pd.DataFrame(
    {
        "week": ["2026-05-01", "2026-05-08", "2026-05-15"],
        "conversion_rate": [0.12, 0.14, 0.16],
    }
)

chart = Chart.trend(
    data=df,
    x="week",
    y="conversion_rate",
    claim="Conversion improved after onboarding launch",
    source="warehouse.funnel_events",
    unit="conversion rate",
    event={"x": "2026-05-08", "label": "Onboarding launch"},
    caveat="Observational trend; not causal proof.",
)

report = chart.audit()
spec = chart.to_vega_lite()
altair_chart = chart.to_altair()
```

Supported front-door intents in v0.1:

- `Chart.trend()`
- `Chart.rank()`
- `Chart.compare()`
- experimental `audit_spec()`

## Scope and Non-Goals

- Not a full visualization library
- Not a dashboard tool
- Not an AI chart generator
- No automatic chart correction in v0.1

## Design Principles

- Claim first
- Data contract before rendering
- Audit before sharing
- Visual integrity over decoration
- Provenance and caveats visible

The audit layer uses Tufte-inspired visual integrity checks. It does not claim to be Tufte-compliant or Tufte-certified.

## Companion Artifact

This repo was built using `ai-engineering-skills` and is intended as the software proof artifact companion to `ai-business-skills`.

See the [agent workflow case study](docs/AGENT_WORKFLOW_CASE_STUDY.md) and [build manifest](artifacts/BUILD_MANIFEST.md) for the proof trail.
