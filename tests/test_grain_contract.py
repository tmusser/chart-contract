from __future__ import annotations

import pandas as pd
import pytest

from chart_contract import Chart, audit_spec, build_transform_lineage


def _severity(report, rule_id: str) -> str:
    return next(f.severity for f in report.findings if f.rule_id == rule_id)


def test_first_party_unique_declared_grain_passes_and_stamps_receipts() -> None:
    frame = pd.DataFrame(
        {
            "segment": ["SMB", "SMB", "Enterprise", "Enterprise"],
            "region": ["East", "West", "East", "West"],
            "revenue": [10.0, 12.0, 15.0, 18.0],
        }
    )
    chart = Chart.compare(
        data=frame,
        x="segment",
        y="revenue",
        group="region",
        claim="Enterprise revenue is higher in both regions.",
        source="synthetic.pipeline",
        unit="dollars",
        title="Revenue by segment and region",
        grain_fields=["segment", "region"],
    )

    report = chart.audit()
    spec = chart.to_vega_lite()

    assert _severity(report, "contract.grain.declared") == "PASS"
    assert _severity(report, "data.grain.unique") == "PASS"
    assert _severity(report, "contract.grain.aggregation") == "PASS"
    assert report.verdict == "READY"
    assert spec["usermeta"]["grain_contract"] == {
        "version": 1,
        "source_grain_fields": ["region", "segment"],
        "output_grain_fields": ["region", "segment"],
        "aggregation": None,
        "source_row_count": 4,
        "source_unique_grain_count": 4,
        "output_group_count": 4,
    }


def test_declared_source_grain_duplicate_blocks_fanout() -> None:
    frame = pd.DataFrame(
        {
            "account_id": ["A", "A", "B"],
            "month": ["2026-09", "2026-09", "2026-09"],
            "revenue": [100.0, 100.0, 200.0],
        }
    )
    chart = Chart.compare(
        data=frame,
        x="month",
        y="revenue",
        claim="September revenue is shown.",
        source="synthetic.joined",
        unit="dollars",
        title="September revenue",
        grain_fields=["account_id", "month"],
    )

    report = chart.audit()

    assert _severity(report, "data.grain.unique") == "FAIL"
    assert report.verdict == "BLOCK"


def test_finer_source_grain_without_aggregation_blocks_and_refuses_render() -> None:
    frame = pd.DataFrame(
        {
            "account_id": ["A", "B"],
            "month": ["2026-09", "2026-09"],
            "revenue": [100.0, 200.0],
        }
    )
    chart = Chart.compare(
        data=frame,
        x="month",
        y="revenue",
        claim="September revenue is shown.",
        source="synthetic.accounts",
        unit="dollars",
        title="September revenue",
        grain_fields=["account_id", "month"],
    )

    report = chart.audit()

    assert _severity(report, "data.grain.unique") == "PASS"
    assert _severity(report, "contract.grain.aggregation") == "FAIL"
    assert report.verdict == "BLOCK"
    with pytest.raises(ValueError, match="no explicit aggregation"):
        chart.to_vega_lite()


def test_repeated_display_keys_without_grain_contract_warn() -> None:
    frame = pd.DataFrame(
        {
            "account_id": ["A", "B"],
            "month": ["2026-09", "2026-09"],
            "revenue": [100.0, 200.0],
        }
    )
    chart = Chart.compare(
        data=frame,
        x="month",
        y="revenue",
        claim="September revenue is shown.",
        source="synthetic.accounts",
        unit="dollars",
        title="September revenue",
    )

    report = chart.audit()

    assert _severity(report, "contract.grain.declared") == "WARN"
    assert report.verdict == "REVIEW"


def _aggregate_spec() -> tuple[dict, pd.DataFrame]:
    frame = pd.DataFrame(
        {
            "account_id": ["A", "B", "A", "B"],
            "month": ["2026-08", "2026-08", "2026-09", "2026-09"],
            "revenue": [100.0, 200.0, 120.0, 220.0],
        }
    )
    spec = {
        "mark": "bar",
        "title": "Monthly account revenue",
        "encoding": {
            "x": {"field": "month", "type": "ordinal"},
            "y": {"field": "revenue", "type": "quantitative", "aggregate": "sum"},
        },
        "usermeta": {
            "source": "synthetic.accounts",
            "unit": "dollars",
            "grain_contract": {
                "version": 1,
                "source_grain_fields": ["account_id", "month"],
                "output_grain_fields": ["month"],
                "aggregation": {"op": "sum", "field": "revenue"},
                "source_row_count": 4,
                "source_unique_grain_count": 4,
                "output_group_count": 2,
            },
            "transform_contract": {"declared": ["aggregate"]},
        },
    }
    spec["usermeta"]["transform_lineage"] = build_transform_lineage(spec)
    return spec, frame


def test_external_encoding_aggregation_matches_grain_contract() -> None:
    spec, frame = _aggregate_spec()

    report = audit_spec(
        spec,
        data=frame,
        claim="Monthly revenue is summed across accounts.",
    )

    assert _severity(report, "contract.grain.declared") == "PASS"
    assert _severity(report, "data.grain.unique") == "PASS"
    assert _severity(report, "contract.grain.aggregation") == "PASS"
    assert report.verdict == "READY"


def test_external_aggregation_without_grain_contract_blocks() -> None:
    spec, frame = _aggregate_spec()
    del spec["usermeta"]["grain_contract"]

    report = audit_spec(
        spec,
        data=frame,
        claim="Monthly revenue is summed across accounts.",
    )

    assert _severity(report, "contract.grain.aggregation") == "FAIL"
    assert report.verdict == "BLOCK"


def test_external_grain_aggregation_op_drift_blocks() -> None:
    spec, frame = _aggregate_spec()
    spec["usermeta"]["grain_contract"]["aggregation"]["op"] = "mean"

    report = audit_spec(
        spec,
        data=frame,
        claim="Monthly revenue is summed across accounts.",
    )

    assert _severity(report, "contract.grain.aggregation") == "FAIL"
    assert report.verdict == "BLOCK"


def test_external_stale_grain_receipt_blocks() -> None:
    spec, frame = _aggregate_spec()
    spec["usermeta"]["grain_contract"]["output_group_count"] = 3

    report = audit_spec(
        spec,
        data=frame,
        claim="Monthly revenue is summed across accounts.",
    )

    assert _severity(report, "contract.grain.aggregation") == "FAIL"


def test_external_duplicate_source_grain_blocks_even_when_aggregate_is_declared() -> None:
    spec, _ = _aggregate_spec()
    frame = pd.DataFrame(
        {
            "account_id": ["A", "A", "B"],
            "month": ["2026-09", "2026-09", "2026-09"],
            "revenue": [100.0, 100.0, 200.0],
        }
    )
    spec["usermeta"]["grain_contract"].update(
        source_row_count=3,
        source_unique_grain_count=2,
        output_group_count=1,
    )

    report = audit_spec(
        spec,
        data=frame,
        claim="September revenue is summed across accounts.",
    )

    assert _severity(report, "data.grain.unique") == "FAIL"
    assert report.verdict == "BLOCK"


def test_grain_contract_is_closed_schema() -> None:
    spec, frame = _aggregate_spec()
    spec["usermeta"]["grain_contract"]["dedupe"] = True

    report = audit_spec(
        spec,
        data=frame,
        claim="Monthly revenue is summed across accounts.",
    )

    assert _severity(report, "contract.grain.declared") == "FAIL"


def test_histogram_binned_count_does_not_require_business_grain_contract() -> None:
    frame = pd.DataFrame({"amount": list(range(20))})
    spec = Chart.histogram(
        data=frame,
        value="amount",
        claim="Observed amount distribution.",
        source="synthetic.amounts",
        unit="dollars",
        title="Observed amount distribution",
    ).to_vega_lite()

    report = audit_spec(spec, data=frame, claim="Observed amount distribution.")

    assert all(
        finding.rule_id not in {"contract.grain.declared", "data.grain.unique", "contract.grain.aggregation"}
        for finding in report.findings
    )


def test_multiple_encoding_aggregates_are_out_of_scope_for_v1() -> None:
    spec, frame = _aggregate_spec()
    spec["encoding"]["tooltip"] = [
        {"field": "revenue", "type": "quantitative", "aggregate": "mean"}
    ]
    spec["usermeta"]["transform_contract"] = {"declared": ["aggregate"]}
    spec["usermeta"]["transform_lineage"] = build_transform_lineage(spec)

    report = audit_spec(
        spec,
        data=frame,
        claim="Monthly revenue is summarized across accounts.",
    )

    assert _severity(report, "contract.grain.aggregation") == "FAIL"
    assert report.verdict == "BLOCK"
