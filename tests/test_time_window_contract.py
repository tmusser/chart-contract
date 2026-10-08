from __future__ import annotations

import pandas as pd

from chart_contract import Chart, audit_spec


def _severity(report, rule_id: str) -> str:
    return next(f.severity for f in report.findings if f.rule_id == rule_id)


def _calendar_chart(
    *,
    baseline_start="2026-09-01",
    baseline_end="2026-09-30",
    target_start="2026-10-01",
    target_end="2026-10-31",
    baseline_complete=True,
    target_complete=True,
) -> Chart:
    return Chart.trend(
        data=pd.DataFrame(
            {
                "period": ["2026-09-01", "2026-10-01"],
                "orders": [100.0, 120.0],
            }
        ),
        x="period",
        y="orders",
        claim="October orders are higher than September orders.",
        source="synthetic.orders",
        unit="count",
        title="Monthly orders",
        baseline_field="period",
        baseline_value="2026-09-01",
        target_value="2026-10-01",
        change_type="absolute",
        declared_change=20.0,
        window_kind="calendar",
        window_granularity="month",
        baseline_start=baseline_start,
        baseline_end=baseline_end,
        target_start=target_start,
        target_end=target_end,
        baseline_complete=baseline_complete,
        target_complete=target_complete,
    )


def test_temporal_comparison_without_window_contract_requires_review() -> None:
    chart = Chart.trend(
        data=pd.DataFrame(
            {
                "period": ["2026-09-01", "2026-10-01"],
                "orders": [100.0, 120.0],
            }
        ),
        x="period",
        y="orders",
        claim="October orders are higher than September orders.",
        source="synthetic.orders",
        unit="count",
        title="Monthly orders",
        baseline_field="period",
        baseline_value="2026-09-01",
        target_value="2026-10-01",
        change_type="absolute",
        declared_change=20.0,
    )

    report = chart.audit()

    assert _severity(report, "contract.time_window.period") == "WARN"
    assert report.verdict == "REVIEW"


def test_complete_calendar_months_surface_unequal_day_count_as_review() -> None:
    report = _calendar_chart().audit()

    assert _severity(report, "contract.time_window.period") == "PASS"
    assert _severity(report, "data.time_window.completeness") == "PASS"
    assert _severity(report, "data.time_window.duration") == "WARN"
    assert report.verdict == "REVIEW"


def test_full_month_vs_month_to_date_blocks() -> None:
    report = _calendar_chart(
        target_end="2026-10-06",
        target_complete=False,
    ).audit()

    assert _severity(report, "data.time_window.completeness") == "FAIL"
    assert _severity(report, "data.time_window.duration") == "WARN"
    assert report.verdict == "BLOCK"


def test_complete_calendar_period_must_match_declared_granularity() -> None:
    report = _calendar_chart(
        target_end="2026-10-06",
        target_complete=True,
    ).audit()

    assert _severity(report, "contract.time_window.period") == "FAIL"
    assert report.verdict == "BLOCK"


def test_equal_rolling_windows_are_ready() -> None:
    chart = Chart.trend(
        data=pd.DataFrame(
            {
                "period": ["baseline", "target"],
                "orders": [100.0, 120.0],
            }
        ),
        x="period",
        y="orders",
        claim="Target-window orders are higher.",
        source="synthetic.orders",
        unit="count",
        title="Rolling 28-day orders",
        baseline_field="period",
        baseline_value="baseline",
        target_value="target",
        change_type="absolute",
        declared_change=20.0,
        window_kind="rolling",
        window_granularity=None,
        baseline_start="2026-08-01",
        baseline_end="2026-08-28",
        target_start="2026-09-01",
        target_end="2026-09-28",
        baseline_complete=True,
        target_complete=True,
    )

    report = chart.audit()

    assert _severity(report, "data.time_window.completeness") == "PASS"
    assert _severity(report, "data.time_window.duration") == "PASS"
    assert report.verdict == "READY"


def test_unequal_rolling_windows_block_without_normalization() -> None:
    chart = Chart.trend(
        data=pd.DataFrame(
            {
                "period": ["baseline", "target"],
                "orders": [100.0, 120.0],
            }
        ),
        x="period",
        y="orders",
        claim="Target-window orders are higher.",
        source="synthetic.orders",
        unit="count",
        title="Rolling-window orders",
        baseline_field="period",
        baseline_value="baseline",
        target_value="target",
        change_type="absolute",
        declared_change=20.0,
        window_kind="rolling",
        window_granularity=None,
        baseline_start="2026-08-01",
        baseline_end="2026-08-28",
        target_start="2026-09-01",
        target_end="2026-09-30",
        baseline_complete=True,
        target_complete=True,
    )

    report = chart.audit()

    assert _severity(report, "data.time_window.duration") == "FAIL"
    assert report.verdict == "BLOCK"


def test_both_incomplete_windows_require_review() -> None:
    chart = Chart.trend(
        data=pd.DataFrame(
            {
                "period": ["baseline", "target"],
                "orders": [100.0, 120.0],
            }
        ),
        x="period",
        y="orders",
        claim="Target partial window is higher.",
        source="synthetic.orders",
        unit="count",
        title="Partial-window orders",
        baseline_field="period",
        baseline_value="baseline",
        target_value="target",
        change_type="absolute",
        declared_change=20.0,
        window_kind="rolling",
        window_granularity=None,
        baseline_start="2026-08-01",
        baseline_end="2026-08-20",
        target_start="2026-09-01",
        target_end="2026-09-20",
        baseline_complete=False,
        target_complete=False,
    )

    report = chart.audit()

    assert _severity(report, "data.time_window.completeness") == "WARN"
    assert _severity(report, "data.time_window.duration") == "PASS"
    assert report.verdict == "REVIEW"


def test_first_party_spec_stamps_time_window_receipts() -> None:
    spec = _calendar_chart().to_vega_lite()

    assert spec["usermeta"]["time_window_contract"] == {
        "version": 1,
        "window_kind": "calendar",
        "window_granularity": "month",
        "baseline_start": "2026-09-01",
        "baseline_end": "2026-09-30",
        "target_start": "2026-10-01",
        "target_end": "2026-10-31",
        "baseline_complete": True,
        "target_complete": True,
        "baseline_days": 30,
        "target_days": 31,
    }


def _spec() -> tuple[dict, pd.DataFrame]:
    chart = _calendar_chart()
    return chart.to_vega_lite(), chart.data.copy()


def test_external_time_window_contract_reaudits() -> None:
    spec, frame = _spec()

    report = audit_spec(
        spec,
        data=frame,
        claim="October orders are higher than September orders.",
    )

    assert _severity(report, "contract.time_window.period") == "PASS"
    assert _severity(report, "data.time_window.completeness") == "PASS"
    assert _severity(report, "data.time_window.duration") == "WARN"
    assert report.verdict == "REVIEW"


def test_stale_day_count_receipt_blocks() -> None:
    spec, frame = _spec()
    spec["usermeta"]["time_window_contract"]["target_days"] = 30

    report = audit_spec(
        spec,
        data=frame,
        claim="October orders are higher than September orders.",
    )

    assert _severity(report, "contract.time_window.period") == "FAIL"
    assert report.verdict == "BLOCK"


def test_time_window_without_comparison_contract_blocks() -> None:
    spec, frame = _spec()
    del spec["usermeta"]["comparison_contract"]

    report = audit_spec(
        spec,
        data=frame,
        claim="October orders are higher than September orders.",
    )

    assert _severity(report, "contract.time_window.period") == "FAIL"
    assert report.verdict == "BLOCK"


def test_rolling_window_cannot_declare_calendar_granularity() -> None:
    chart = Chart.trend(
        data=pd.DataFrame({"period": ["a", "b"], "orders": [1.0, 2.0]}),
        x="period",
        y="orders",
        claim="Target is higher.",
        source="synthetic.orders",
        unit="count",
        title="Orders",
        baseline_field="period",
        baseline_value="a",
        target_value="b",
        change_type="absolute",
        declared_change=1.0,
        window_kind="rolling",
        window_granularity="month",
        baseline_start="2026-08-01",
        baseline_end="2026-08-28",
        target_start="2026-09-01",
        target_end="2026-09-28",
        baseline_complete=True,
        target_complete=True,
    )

    report = chart.audit()

    assert _severity(report, "contract.time_window.period") == "FAIL"
    assert report.verdict == "BLOCK"
