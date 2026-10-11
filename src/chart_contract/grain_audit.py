"""Audit declared source grain and explicit aggregation semantics."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from .audit import FAIL, PASS, WARN, AuditReport
from .grain import (
    GRAIN_INTENTS,
    build_grain_summary,
    encoding_aggregation,
    normalize_grain_fields,
    parse_grain_contract,
    visible_grain_fields_for_chart,
    visible_grain_fields_from_encoding,
)


def audit_grain_chart(report: AuditReport, chart: Any) -> None:
    if getattr(chart, "intent", None) not in GRAIN_INTENTS:
        return

    output_fields = visible_grain_fields_for_chart(chart)
    raw_grain = getattr(chart, "grain_fields", None)

    if raw_grain is None:
        if output_fields and _has_duplicate_keys(chart.data, output_fields):
            report.add(
                "contract.grain.declared",
                WARN,
                (
                    f"Multiple source rows share the displayed grain {list(output_fields)!r}, "
                    "but no source grain is declared."
                ),
                suggestion=(
                    "Declare grain_fields=[...] so duplicate source keys and hidden "
                    "many-to-one display collapse can be audited."
                ),
                field="grain_fields",
            )
        else:
            report.add(
                "contract.grain.declared",
                PASS,
                "No repeated displayed-grain keys require an explicit source-grain declaration.",
            )
        return

    try:
        source_fields = normalize_grain_fields(raw_grain)
    except ValueError as exc:
        report.add(
            "contract.grain.declared",
            FAIL,
            str(exc),
            suggestion="Declare a non-empty unique list of source grain fields.",
            field="grain_fields",
        )
        return

    report.add(
        "contract.grain.declared",
        PASS,
        f"Source row grain is explicitly declared as {list(source_fields)!r}.",
    )

    issue = _source_grain_issue(chart.data, source_fields)
    if issue is not None:
        report.add(
            "data.grain.unique",
            FAIL,
            issue,
            suggestion=(
                "Repair join fanout/duplicate source rows or declare the actual finer grain; "
                "do not silently aggregate duplicate grain keys."
            ),
            field="grain_fields",
        )
        return
    report.add(
        "data.grain.unique",
        PASS,
        "Every supplied row is unique at the declared source grain.",
    )

    if not output_fields:
        return
    output_groups = _group_count(chart.data, output_fields)
    if output_groups != len(chart.data):
        report.add(
            "contract.grain.aggregation",
            FAIL,
            (
                f"{len(chart.data)} unique source-grain rows map to {output_groups} displayed "
                f"grain group(s) {list(output_fields)!r}, but first-party v1 performs no "
                "implicit aggregation."
            ),
            suggestion=(
                "Aggregate upstream with an explicitly chosen operation, then pass one row per "
                "displayed grain. chart-contract will not guess sum vs mean vs another operation."
            ),
            field="grain_fields",
        )
    else:
        report.add(
            "contract.grain.aggregation",
            PASS,
            "Declared source grain maps one-to-one to the displayed grain; no aggregation is required.",
        )


def audit_grain_spec(
    report: AuditReport,
    spec: Mapping[str, Any],
    analytical_spec: Mapping[str, Any],
    encoding: Any,
    frame: pd.DataFrame | None,
) -> None:
    output_fields = visible_grain_fields_from_encoding(encoding)
    try:
        actual_aggregation = encoding_aggregation(encoding)
    except ValueError as exc:
        report.add(
            "contract.grain.aggregation",
            FAIL,
            str(exc),
            suggestion="Use at most one supported encoding-level aggregate in grain-contract v1.",
            field="encoding",
        )
        return

    try:
        contract = parse_grain_contract(spec)
    except ValueError as exc:
        report.add(
            "contract.grain.declared",
            FAIL,
            str(exc),
            suggestion="Use the exact closed version-1 grain_contract schema.",
            field="usermeta.grain_contract",
        )
        return

    if contract is None:
        if actual_aggregation is not None:
            report.add(
                "contract.grain.aggregation",
                FAIL,
                (
                    f"Spec collapses rows with {actual_aggregation['op']}("
                    f"{actual_aggregation['field']}) but declares no source/output grain contract."
                ),
                suggestion=(
                    "Declare usermeta.grain_contract so the pre-aggregation source grain and "
                    "displayed output grain are explicit."
                ),
                field="usermeta.grain_contract",
            )
            return
        if frame is not None and output_fields and _has_duplicate_keys(frame, output_fields):
            report.add(
                "contract.grain.declared",
                WARN,
                (
                    f"Supplied evidence contains repeated displayed-grain keys "
                    f"{list(output_fields)!r} without a grain contract."
                ),
                suggestion="Declare source_grain_fields or reduce the evidence to one row per displayed key.",
                field="usermeta.grain_contract",
            )
        else:
            report.add(
                "contract.grain.declared",
                PASS,
                "No declared or structurally required grain contract was detected.",
            )
        return

    report.add(
        "contract.grain.declared",
        PASS,
        (
            f"Spec declares source grain {contract['source_grain_fields']!r} and output grain "
            f"{contract['output_grain_fields']!r}."
        ),
    )

    if tuple(contract["output_grain_fields"]) != output_fields:
        report.add(
            "contract.grain.aggregation",
            FAIL,
            (
                f"Declared output grain {contract['output_grain_fields']!r} does not match "
                f"visible encoded grain {list(output_fields)!r}."
            ),
            suggestion="Regenerate grain_contract from the final spec encodings.",
            field="usermeta.grain_contract.output_grain_fields",
        )
        return

    if frame is None:
        report.add(
            "data.grain.unique",
            FAIL,
            "Grain contract cannot be verified without reconstructable source evidence.",
            suggestion="Supply the pre-aggregation evidence rows used by the spec.",
            field="usermeta.grain_contract",
        )
        return

    source_fields = tuple(contract["source_grain_fields"])
    issue = _source_grain_issue(frame, source_fields)
    if issue is not None:
        report.add(
            "data.grain.unique",
            FAIL,
            issue,
            suggestion="Repair duplicate/null grain keys before aggregation or visualization.",
            field="usermeta.grain_contract.source_grain_fields",
        )
        return
    report.add(
        "data.grain.unique",
        PASS,
        "Supplied evidence is unique at the declared source grain.",
    )

    declared_aggregation = contract["aggregation"]
    if declared_aggregation != actual_aggregation:
        report.add(
            "contract.grain.aggregation",
            FAIL,
            (
                f"Declared grain aggregation {declared_aggregation!r} does not match the "
                f"spec's encoding aggregation {actual_aggregation!r}."
            ),
            suggestion="Make the grain aggregation declaration exactly match the final encoding.",
            field="usermeta.grain_contract.aggregation",
        )
        return

    try:
        expected = build_grain_summary(
            frame,
            source_grain_fields=source_fields,
            output_grain_fields=output_fields,
            aggregation=actual_aggregation,
        ).to_dict()
    except ValueError as exc:
        report.add(
            "contract.grain.aggregation",
            FAIL,
            str(exc),
            suggestion="Declare the actual aggregation or provide one row per displayed grain.",
            field="usermeta.grain_contract",
        )
        return

    receipt_fields = ("source_row_count", "source_unique_grain_count", "output_group_count")
    drift = [name for name in receipt_fields if contract[name] != expected[name]]
    if drift:
        report.add(
            "contract.grain.aggregation",
            FAIL,
            "Grain receipt counts are stale: " + ", ".join(drift) + ".",
            suggestion="Regenerate grain_contract from the final source evidence and spec.",
            field="usermeta.grain_contract",
        )
        return

    if actual_aggregation is None:
        report.add(
            "contract.grain.aggregation",
            PASS,
            "Source grain maps one-to-one to output grain; no aggregation is present.",
        )
    else:
        report.add(
            "contract.grain.aggregation",
            PASS,
            (
                f"Explicit {actual_aggregation['op']}({actual_aggregation['field']}) aggregation "
                "matches the declared source/output grain contract."
            ),
        )


def _source_grain_issue(frame: pd.DataFrame, fields: tuple[str, ...]) -> str | None:
    missing = sorted(set(fields) - set(frame.columns))
    if missing:
        return "Declared source grain references missing field(s): " + ", ".join(missing) + "."
    for field in fields:
        if frame[field].isna().any():
            return f"Declared source grain field {field!r} contains null values."
    duplicated = frame.duplicated(subset=list(fields), keep=False)
    if duplicated.any():
        return (
            f"Declared source grain {list(fields)!r} is not unique; "
            f"{int(duplicated.sum())} rows participate in duplicate grain keys."
        )
    return None


def _has_duplicate_keys(frame: pd.DataFrame, fields: tuple[str, ...]) -> bool:
    if not fields or any(field not in frame.columns for field in fields):
        return False
    return bool(frame.duplicated(subset=list(fields), keep=False).any())


def _group_count(frame: pd.DataFrame, fields: tuple[str, ...]) -> int:
    if not len(frame):
        return 0
    return int(frame.groupby(list(fields), dropna=False).ngroups)
