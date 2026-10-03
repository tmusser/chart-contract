from __future__ import annotations

from copy import deepcopy

import pandas as pd

from chart_contract import Chart, audit_spec, build_transform_lineage


def _data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "region": ["East", "West", "East", "West"],
            "revenue": [100.0, 120.0, 150.0, 160.0],
            "users": [10, 12, 15, 16],
        }
    )


def _base_spec():
    return {
        "mark": "point",
        "title": "Revenue per user",
        "encoding": {
            "x": {"field": "region", "type": "nominal"},
            "y": {"field": "revenue", "type": "quantitative"},
        },
        "usermeta": {
            "source": "synthetic.revenue",
            "unit": "dollars",
        },
    }


def _finding(report):
    return next(
        finding
        for finding in report.findings
        if finding.rule_id == "transform.lineage.receipts"
    )


def test_no_transform_spec_needs_no_lineage_receipt() -> None:
    report = audit_spec(
        spec=_base_spec(),
        data=_data(),
        claim="Observed revenue differs by region.",
    )

    finding = _finding(report)

    assert finding.severity == "PASS"
    assert "No transform lineage receipts are required" in finding.message


def test_transformed_spec_blocks_without_lineage_receipts() -> None:
    spec = _base_spec()
    spec["transform"] = [{"filter": "datum.region === 'East'"}]
    spec["usermeta"]["transform_contract"] = {"declared": ["filter"]}

    report = audit_spec(
        spec=spec,
        data=_data(),
        claim="Observed East-region revenue is shown.",
    )

    finding = _finding(report)

    assert report.verdict == "BLOCK"
    assert finding.severity == "FAIL"
    assert "without lineage receipts" in finding.message


def test_exact_lineage_receipt_passes_and_extracts_calculate_fields() -> None:
    spec = _base_spec()
    spec["transform"] = [
        {
            "calculate": "datum.revenue / datum.users",
            "as": "revenue_per_user",
        }
    ]
    spec["encoding"]["y"] = {
        "field": "revenue",
        "type": "quantitative",
    }
    spec["usermeta"]["transform_contract"] = {"declared": ["calculate"]}
    lineage = build_transform_lineage(spec)
    spec["usermeta"]["transform_lineage"] = lineage

    receipt = lineage["receipts"][0]
    assert receipt["kind"] == "calculate"
    assert receipt["location"] == "transform[0].calculate"
    assert receipt["input_fields"] == ["revenue", "users"]
    assert receipt["output_fields"] == ["revenue_per_user"]
    assert len(receipt["operation_sha256"]) == 64

    report = audit_spec(
        spec=spec,
        data=_data(),
        claim="Observed revenue differs by region.",
    )

    assert _finding(report).severity == "PASS"


def test_changed_transform_payload_invalidates_existing_receipt() -> None:
    spec = _base_spec()
    spec["transform"] = [{"filter": "datum.region === 'East'"}]
    spec["usermeta"]["transform_contract"] = {"declared": ["filter"]}
    spec["usermeta"]["transform_lineage"] = build_transform_lineage(spec)

    spec["transform"][0]["filter"] = "datum.region === 'West'"

    report = audit_spec(
        spec=spec,
        data=_data(),
        claim="Observed West-region revenue is shown.",
    )

    finding = _finding(report)

    assert report.verdict == "BLOCK"
    assert finding.severity == "FAIL"
    assert "changed receipt(s): transform[0].filter" in finding.message


def test_stale_lineage_receipt_blocks_after_transform_removed() -> None:
    spec = _base_spec()
    spec["transform"] = [{"filter": "datum.region === 'East'"}]
    lineage = build_transform_lineage(spec)
    del spec["transform"]
    spec["usermeta"]["transform_lineage"] = lineage

    report = audit_spec(
        spec=spec,
        data=_data(),
        claim="Observed revenue differs by region.",
    )

    finding = _finding(report)

    assert report.verdict == "BLOCK"
    assert finding.severity == "FAIL"
    assert "stale" in finding.message.lower()


def test_malformed_lineage_hash_blocks() -> None:
    spec = _base_spec()
    spec["transform"] = [{"filter": "datum.region === 'East'"}]
    spec["usermeta"]["transform_contract"] = {"declared": ["filter"]}
    lineage = build_transform_lineage(spec)
    lineage["receipts"][0]["operation_sha256"] = "not-a-hash"
    spec["usermeta"]["transform_lineage"] = lineage

    report = audit_spec(
        spec=spec,
        data=_data(),
        claim="Observed East-region revenue is shown.",
    )

    assert report.verdict == "BLOCK"
    assert _finding(report).severity == "FAIL"


def test_lineage_hash_is_key_order_invariant_for_transform_object() -> None:
    spec_a = _base_spec()
    spec_a["transform"] = [
        {
            "calculate": "datum.revenue / datum.users",
            "as": "revenue_per_user",
        }
    ]
    spec_b = deepcopy(spec_a)
    spec_b["transform"] = [
        {
            "as": "revenue_per_user",
            "calculate": "datum.revenue / datum.users",
        }
    ]

    assert (
        build_transform_lineage(spec_a)["receipts"][0]["operation_sha256"]
        == build_transform_lineage(spec_b)["receipts"][0]["operation_sha256"]
    )


def test_first_party_histogram_stamps_exact_lineage_receipts() -> None:
    spec = Chart.histogram(
        data=pd.DataFrame({"amount": list(range(30))}),
        value="amount",
        bins=10,
        claim="Observed amounts span the measured range.",
        source="synthetic.amounts",
        unit="dollars",
        title="Observed amount distribution",
    ).to_vega_lite()

    assert spec["usermeta"]["transform_lineage"] == build_transform_lineage(spec)
    assert {
        receipt["kind"]
        for receipt in spec["usermeta"]["transform_lineage"]["receipts"]
    } == {"aggregate", "bin"}


def test_first_party_violin_stamps_density_field_lineage() -> None:
    spec = Chart.violin(
        data=pd.DataFrame({"amount": list(range(30))}),
        y="amount",
        claim="Observed amounts show a continuous distribution.",
        source="synthetic.amounts",
        unit="dollars",
        title="Observed amount distribution",
    ).to_vega_lite()

    lineage = spec["usermeta"]["transform_lineage"]
    density_receipt = next(
        receipt for receipt in lineage["receipts"] if receipt["kind"] == "density"
    )

    assert lineage == build_transform_lineage(spec)
    assert density_receipt["input_fields"] == ["_distribution", "amount"]
    assert density_receipt["output_fields"] == ["density", "value"]
