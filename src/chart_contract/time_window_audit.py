"""Audit time-window comparability for baseline comparisons."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from .audit import FAIL, PASS, WARN, AuditReport
from .comparison import COMPARISON_CONTRACT_KEY, comparison_declaration, parse_comparison_contract
from .contracts import is_datetime_like
from .time_window import (
    TIME_WINDOW_CONTRACT_KEY,
    build_time_window_summary,
    parse_time_window_contract,
    time_window_declaration,
)


def audit_time_window_chart(report: AuditReport, chart: Any) -> None:
    comparison = comparison_declaration(chart)
    declaration = time_window_declaration(chart)

    if declaration is None:
        if _chart_temporal_comparison(chart, comparison):
            report.add(
                "contract.time_window.period",
                WARN,
                "Temporal baseline comparison does not declare explicit baseline/target windows.",
                suggestion=(
                    "Declare calendar or rolling baseline/target start/end dates and completeness."
                ),
                field="window_kind",
            )
        return

    if comparison is None:
        report.add(
            "contract.time_window.period",
            FAIL,
            "Time-window metadata requires an explicit comparison baseline contract.",
            suggestion="Declare baseline_field/baseline_value/target_value and change semantics first.",
            field="window_kind",
        )
        return

    try:
        summary = build_time_window_summary(**declaration)
    except ValueError as exc:
        report.add(
            "contract.time_window.period",
            FAIL,
            str(exc),
            suggestion="Use canonical ISO dates and a valid calendar/rolling v1 window contract.",
            field="window_kind",
        )
        return

    report.add(
        "contract.time_window.period",
        PASS,
        (
            f"Time windows are explicit: {summary.window_kind} "
            f"{summary.window_granularity or 'window'}; "
            f"baseline {summary.baseline_start}..{summary.baseline_end}, "
            f"target {summary.target_start}..{summary.target_end}."
        ),
    )
    _audit_completeness(report, summary.to_dict())
    _audit_duration(report, summary.to_dict())


def audit_time_window_spec(
    report: AuditReport,
    spec: Mapping[str, Any],
    frame: pd.DataFrame | None,
) -> None:
    usermeta = spec.get("usermeta")
    has_time = isinstance(usermeta, Mapping) and TIME_WINDOW_CONTRACT_KEY in usermeta

    try:
        comparison = parse_comparison_contract(spec)
    except ValueError:
        # Comparison audit reports malformed comparison metadata separately.
        comparison = None

    if not has_time:
        if comparison is not None and _spec_temporal_comparison(frame, comparison):
            report.add(
                "contract.time_window.period",
                WARN,
                "Temporal comparison spec has no time_window_contract.",
                suggestion=(
                    "Declare calendar or rolling baseline/target start/end dates and completeness."
                ),
                field="usermeta.time_window_contract",
            )
        return

    if not isinstance(usermeta, Mapping) or COMPARISON_CONTRACT_KEY not in usermeta:
        report.add(
            "contract.time_window.period",
            FAIL,
            "time_window_contract requires a comparison_contract.",
            suggestion="Bind the time windows to an explicit baseline comparison contract.",
            field="usermeta.time_window_contract",
        )
        return

    try:
        contract = parse_time_window_contract(spec)
    except ValueError as exc:
        report.add(
            "contract.time_window.period",
            FAIL,
            str(exc),
            suggestion="Use the exact closed version-1 time-window contract schema.",
            field="usermeta.time_window_contract",
        )
        return
    if contract is None:
        return

    try:
        expected = build_time_window_summary(
            window_kind=contract["window_kind"],
            window_granularity=contract["window_granularity"],
            baseline_start=contract["baseline_start"],
            baseline_end=contract["baseline_end"],
            target_start=contract["target_start"],
            target_end=contract["target_end"],
            baseline_complete=contract["baseline_complete"],
            target_complete=contract["target_complete"],
        ).to_dict()
    except ValueError as exc:
        report.add(
            "contract.time_window.period",
            FAIL,
            str(exc),
            field="usermeta.time_window_contract",
        )
        return

    stale = [
        field
        for field in ("baseline_days", "target_days")
        if contract[field] != expected[field]
    ]
    if stale:
        report.add(
            "contract.time_window.period",
            FAIL,
            "Time-window day-count receipts are stale: " + ", ".join(stale) + ".",
            suggestion="Regenerate time_window_contract from the final declared windows.",
            field="usermeta.time_window_contract",
        )
        return

    report.add(
        "contract.time_window.period",
        PASS,
        "Time-window contract is structurally valid and day-count receipts are current.",
    )
    _audit_completeness(report, contract)
    _audit_duration(report, contract)


def _audit_completeness(report: AuditReport, contract: Mapping[str, Any]) -> None:
    baseline_complete = bool(contract["baseline_complete"])
    target_complete = bool(contract["target_complete"])
    if baseline_complete and target_complete:
        report.add(
            "data.time_window.completeness",
            PASS,
            "Baseline and target windows are both declared complete.",
        )
    elif baseline_complete != target_complete:
        report.add(
            "data.time_window.completeness",
            FAIL,
            "Comparison mixes one complete period with one incomplete period.",
            suggestion=(
                "Compare like-for-like completed periods or wait/narrow both windows; "
                "chart-contract will not prorate or normalize automatically."
            ),
            field="usermeta.time_window_contract" if isinstance(contract, dict) else None,
        )
    else:
        report.add(
            "data.time_window.completeness",
            WARN,
            "Both comparison windows are declared incomplete.",
            suggestion="Review whether the incomplete windows represent like-for-like exposure.",
        )


def _audit_duration(report: AuditReport, contract: Mapping[str, Any]) -> None:
    baseline_days = int(contract["baseline_days"])
    target_days = int(contract["target_days"])
    kind = contract["window_kind"]

    if kind == "rolling":
        if baseline_days != target_days:
            report.add(
                "data.time_window.duration",
                FAIL,
                (
                    f"Rolling comparison windows differ in duration: "
                    f"{baseline_days} vs {target_days} inclusive days."
                ),
                suggestion=(
                    "Use equal-duration rolling windows; do not silently normalize unequal exposure."
                ),
            )
        else:
            report.add(
                "data.time_window.duration",
                PASS,
                f"Rolling comparison windows both span {baseline_days} inclusive days.",
            )
        return

    if baseline_days == target_days:
        report.add(
            "data.time_window.duration",
            PASS,
            f"Calendar comparison windows both span {baseline_days} inclusive days.",
        )
    else:
        report.add(
            "data.time_window.duration",
            WARN,
            (
                f"Calendar periods differ in duration: "
                f"{baseline_days} vs {target_days} inclusive days."
            ),
            suggestion=(
                "Review whether the metric is exposure-sensitive before comparing raw totals; "
                "no automatic normalization is applied."
            ),
        )


def _chart_temporal_comparison(chart: Any, comparison: Mapping[str, Any] | None) -> bool:
    if comparison is None:
        return False
    field = comparison.get("baseline_field")
    return bool(
        isinstance(field, str)
        and field in chart.data.columns
        and is_datetime_like(chart.data[field])
    )


def _spec_temporal_comparison(
    frame: pd.DataFrame | None,
    comparison: Mapping[str, Any],
) -> bool:
    if frame is None:
        return False
    field = comparison.get("baseline_field")
    return bool(
        isinstance(field, str)
        and field in frame.columns
        and is_datetime_like(frame[field])
    )
