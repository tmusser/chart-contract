"""First-party and external-spec freshness evidence audits."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from .audit import FAIL, PASS, WARN, AuditReport
from .freshness import (
    FRESHNESS_CONTRACT_KEY,
    FRESHNESS_INTENTS,
    build_freshness_contract,
    freshness_declaration,
    freshness_status,
    parse_freshness_contract,
    validate_declaration,
)


def _status_findings(report: AuditReport, contract: Mapping[str, Any]) -> None:
    (age_ok, age_message), (final_severity, final_message) = freshness_status(contract)
    report.add(
        "data.freshness.age", PASS if age_ok else FAIL, age_message,
        suggestion=None if age_ok else "Refresh source data or explicitly revise the report's freshness requirement.",
    )
    report.add(
        "data.freshness.finalization", final_severity, final_message,
        suggestion=(
            None if final_severity == PASS else
            "Wait for source finalization, narrow the reporting cutoff, or disclose preliminary results."
        ),
    )


def audit_freshness_chart(report: AuditReport, chart: Any) -> None:
    declaration = freshness_declaration(chart)
    if declaration is None:
        return
    if chart.intent not in FRESHNESS_INTENTS:
        report.add("contract.freshness.declared", FAIL, "Freshness v1 supports trend/rank/compare charts.")
        return
    try:
        parsed = validate_declaration(declaration)
    except ValueError as exc:
        report.add("contract.freshness.declared", FAIL, str(exc))
        return
    report.add("contract.freshness.declared", PASS, "Explicit freshness audit date, evidence date field, age policy, and finalized cutoff.")
    try:
        receipt = build_freshness_contract(chart.data, parsed)
    except ValueError as exc:
        report.add("data.freshness.evidence", FAIL, str(exc))
        return
    report.add(
        "data.freshness.evidence", PASS,
        f"Reconstructed data_through={receipt['data_through']} from {receipt['row_count']} source row(s).",
    )
    _status_findings(report, receipt)


def audit_freshness_spec(
    report: AuditReport, spec: Mapping[str, Any], frame: pd.DataFrame | None,
) -> None:
    meta = spec.get("usermeta")
    if not isinstance(meta, Mapping) or FRESHNESS_CONTRACT_KEY not in meta:
        return
    try:
        parsed = parse_freshness_contract(spec)
    except ValueError as exc:
        report.add("contract.freshness.declared", FAIL, str(exc), field="usermeta.freshness_contract")
        return
    if parsed is None:
        return
    report.add("contract.freshness.declared", PASS, "Closed v1 freshness contract declares a deterministic reference date.")
    if frame is None:
        report.add("data.freshness.evidence", FAIL, "Freshness requires reconstructable original data; none was supplied.")
        return
    try:
        current = build_freshness_contract(frame, {
            key: parsed[key] for key in (
                "version", "audit_date", "observation_date_field", "finalized_through",
                "max_age_days", "require_finalized",
            )
        })
    except ValueError as exc:
        report.add("data.freshness.evidence", FAIL, str(exc))
        return
    if current["data_through"] != parsed["data_through"] or current["row_count"] != parsed["row_count"]:
        report.add(
            "data.freshness.evidence", FAIL,
            "Stale freshness receipts: stored data_through/row_count do not match supplied source evidence.",
        )
        return
    report.add(
        "data.freshness.evidence", PASS,
        f"Freshness receipts match {current['row_count']} source row(s), through {current['data_through']}.",
    )
    _status_findings(report, current)
