import pandas as pd
import runpy
from pathlib import Path

from chart_contract import Chart


def test_trend_chart_creates_audit_report_and_spec() -> None:
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

    assert report.passed is True
    assert "layer" in spec
    assert spec["title"]["text"] == "Conversion improved after onboarding launch"


def test_rank_chart_declares_sort() -> None:
    df = pd.DataFrame(
        {
            "segment": ["Free", "Starter", "Pro"],
            "adoption": [120, 200, 150],
        }
    )

    spec = Chart.rank(
        data=df,
        x="segment",
        y="adoption",
        claim="Starter leads adoption across plans",
        source="warehouse.plan_adoption",
        unit="accounts",
    ).to_vega_lite()

    assert spec["encoding"]["y"]["sort"] == "-x"


def test_compare_chart_supports_grouped_bars() -> None:
    df = pd.DataFrame(
        {
            "segment": ["SMB", "SMB", "Enterprise", "Enterprise"],
            "region": ["East", "West", "East", "West"],
            "value": [10, 12, 15, 18],
        }
    )

    spec = Chart.compare(
        data=df,
        x="segment",
        y="value",
        group="region",
        claim="Enterprise leads across regions",
        source="warehouse.pipeline_summary",
        unit="deals",
    ).to_vega_lite()

    assert spec["encoding"]["xOffset"]["field"] == "region"


def test_examples_execute_and_write_specs() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    scripts = [
        "bad_to_good_chart.py",
        "trend_claim.py",
        "rank_claim.py",
        "compare_claim.py",
    ]

    for script in scripts:
        runpy.run_path(str(repo_root / "examples" / script), run_name="__main__")

    output_dir = repo_root / "examples" / "output"
    assert (output_dir / "corrected_chart.vl.json").exists()
    assert (output_dir / "trend_claim.vl.json").exists()
    assert (output_dir / "rank_claim.vl.json").exists()
    assert (output_dir / "compare_claim.vl.json").exists()
