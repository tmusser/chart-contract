from __future__ import annotations

import pandas as pd

from chart_contract import Chart, audit_spec
from chart_contract.transforms import collect_transform_inventory


def _data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "region": ["East", "West", "East"],
            "revenue": [100.0, 120.0, 150.0],
            "users": [10, 12, 15],
        }
    )


def _base_spec(*, transforms=None, declaration=None):
    usermeta = {
        "source": "synthetic.revenue",
        "unit": "dollars",
    }
    if declaration is not None:
        usermeta["transform_contract"] = declaration

    spec = {
        "mark": "line",
        "title": "Observed revenue trend",
        "encoding": {
            "x": {"field": "date", "type": "temporal"},
            "y": {"field": "revenue", "type": "quantitative"},
        },
        "usermeta": usermeta,
    }
    if transforms is not None:
        spec["transform"] = transforms
    return spec


def _findings(report, rule_id: str):
    return [finding for finding in report.findings if finding.rule_id == rule_id]


def test_no_transform_spec_records_empty_inventory_and_passes_contract() -> None:
    report = audit_spec(
        spec=_base_spec(),
        data=_data(),
        claim="Observed revenue changed across the three dates.",
    )

    inventory = _findings(report, "transform.inventory")
    declaration = _findings(report, "transform.declaration")

    assert len(inventory) == 1
    assert inventory[0].severity == "PASS"
    assert "No explicit Vega-Lite analytical transforms" in inventory[0].message
    assert declaration[0].severity == "PASS"


def test_hidden_filter_transform_blocks_without_declaration() -> None:
    report = audit_spec(
        spec=_base_spec(transforms=[{"filter": "datum.region === 'East'"}]),
        data=_data(),
        claim="Observed revenue changed across the three dates.",
    )

    inventory = _findings(report, "transform.inventory")
    declaration = _findings(report, "transform.declaration")

    assert report.verdict == "BLOCK"
    assert any(finding.field == "transform[0].filter" for finding in inventory)
    assert declaration[0].severity == "FAIL"
    assert "filter" in declaration[0].message


def test_exact_transform_declaration_passes_policy() -> None:
    spec = _base_spec(
        transforms=[
            {"filter": "datum.region === 'East'"},
            {"calculate": "datum.revenue / datum.users", "as": "revenue_per_user"},
            {
                "window": [{"op": "rank", "as": "rank"}],
                "sort": [{"field": "revenue", "order": "descending"}],
            },
        ],
        declaration={"declared": ["window", "filter", "calculate", "timeUnit"]},
    )
    spec["encoding"]["x"]["timeUnit"] = "yearmonth"

    report = audit_spec(
        spec=spec,
        data=_data(),
        claim="Observed revenue changed over time.",
    )

    declaration = _findings(report, "transform.declaration")
    inventory = _findings(report, "transform.inventory")
    inventory_pairs = {(finding.field, finding.message) for finding in inventory}

    assert declaration[0].severity == "PASS"
    assert report.verdict != "BLOCK"
    assert any(field == "transform[0].filter" for field, _ in inventory_pairs)
    assert any(field == "transform[1].calculate" for field, _ in inventory_pairs)
    assert any(field == "transform[2].window" for field, _ in inventory_pairs)
    assert any(field == "encoding.x.timeUnit" for field, _ in inventory_pairs)


def test_stale_transform_declaration_blocks() -> None:
    report = audit_spec(
        spec=_base_spec(
            transforms=[{"filter": "datum.region === 'East'"}],
            declaration={"declared": ["filter", "bin"]},
        ),
        data=_data(),
        claim="Observed revenue changed across the three dates.",
    )

    finding = _findings(report, "transform.declaration")[0]

    assert report.verdict == "BLOCK"
    assert finding.severity == "FAIL"
    assert "declared but not detected kinds: bin" in finding.message


def test_malformed_transform_entry_blocks_inventory() -> None:
    report = audit_spec(
        spec=_base_spec(
            transforms=[{"not_a_transform": "datum.revenue"}],
            declaration={"declared": []},
        ),
        data=_data(),
        claim="Observed revenue changed across the three dates.",
    )

    inventory = _findings(report, "transform.inventory")

    assert report.verdict == "BLOCK"
    assert any(finding.severity == "FAIL" for finding in inventory)
    assert any(finding.field == "transform[0]" for finding in inventory)


def test_transform_entry_with_multiple_operators_blocks_inventory() -> None:
    report = audit_spec(
        spec=_base_spec(
            transforms=[{"filter": "datum.region === 'East'", "sample": 2}],
            declaration={"declared": ["filter", "sample"]},
        ),
        data=_data(),
        claim="Observed revenue changed across the three dates.",
    )

    inventory = _findings(report, "transform.inventory")

    assert report.verdict == "BLOCK"
    assert any(finding.severity == "FAIL" for finding in inventory)
    assert any(finding.field == "transform[0]" for finding in inventory)


def test_malformed_transform_declaration_blocks() -> None:
    report = audit_spec(
        spec=_base_spec(
            transforms=[{"filter": "datum.region === 'East'"}],
            declaration={"declared": ["filter"], "approved": True},
        ),
        data=_data(),
        claim="Observed revenue changed across the three dates.",
    )

    finding = _findings(report, "transform.declaration")[0]

    assert report.verdict == "BLOCK"
    assert finding.severity == "FAIL"
    assert "unsupported field" in finding.message


def test_nested_layer_transform_is_inventoried_with_exact_location() -> None:
    spec = {
        "title": "Observed revenue by region",
        "usermeta": {
            "source": "synthetic.revenue",
            "unit": "dollars",
            "transform_contract": {"declared": ["filter"]},
        },
        "layer": [
            {
                "transform": [{"filter": "datum.region === 'East'"}],
                "mark": "line",
                "encoding": {
                    "x": {"field": "date", "type": "temporal"},
                    "y": {"field": "revenue", "type": "quantitative"},
                },
            }
        ],
    }

    report = audit_spec(
        spec=spec,
        data=_data(),
        claim="Observed East-region revenue changed over time.",
    )

    inventory = _findings(report, "transform.inventory")

    assert _findings(report, "transform.declaration")[0].severity == "PASS"
    assert any(finding.field == "layer[0].transform[0].filter" for finding in inventory)


def test_encoding_aggregate_bin_timeunit_and_shorthand_are_inventoried() -> None:
    spec = {
        "mark": "bar",
        "encoding": {
            "x": {"field": "date", "type": "temporal", "timeUnit": "yearmonth"},
            "y": {"field": "revenue", "type": "quantitative", "aggregate": "sum"},
            "color": {"field": "users", "type": "quantitative", "bin": True},
            "tooltip": ["mean(revenue):Q"],
        },
    }

    inventory = collect_transform_inventory(spec)
    kinds = [occurrence.kind for occurrence in inventory.occurrences]
    locations = {occurrence.location for occurrence in inventory.occurrences}

    assert inventory.kinds == ("aggregate", "bin", "timeUnit")
    assert kinds.count("aggregate") == 2
    assert "encoding.x.timeUnit" in locations
    assert "encoding.y.aggregate" in locations
    assert "encoding.color.bin" in locations
    assert "encoding.tooltip[0]" in locations


def test_density_extent_parameter_is_not_misclassified_as_second_transform() -> None:
    spec = {
        "mark": "area",
        "transform": [
            {
                "density": "revenue",
                "extent": [0, 200],
                "as": ["value", "density"],
            }
        ],
        "encoding": {
            "x": {"field": "density", "type": "quantitative"},
            "y": {"field": "value", "type": "quantitative"},
        },
    }

    inventory = collect_transform_inventory(spec)

    assert inventory.kinds == ("density",)
    assert inventory.malformed_locations == ()
    assert inventory.occurrences[0].location == "transform[0].density"


def test_first_party_histogram_declares_emitted_transforms() -> None:
    data = pd.DataFrame({"amount": list(range(30))})

    spec = Chart.histogram(
        data=data,
        value="amount",
        bins=10,
        claim="Observed amounts span the measured range.",
        source="synthetic.amounts",
        unit="dollars",
        title="Observed amount distribution",
    ).to_vega_lite()

    assert spec["usermeta"]["transform_contract"] == {
        "declared": ["aggregate", "bin"]
    }

    inventory = collect_transform_inventory(spec)
    assert inventory.kinds == ("aggregate", "bin")


def test_first_party_violin_declares_density_transform() -> None:
    data = pd.DataFrame({"amount": list(range(30))})

    spec = Chart.violin(
        data=data,
        y="amount",
        claim="Observed amounts show a continuous distribution.",
        source="synthetic.amounts",
        unit="dollars",
        title="Observed amount distribution",
    ).to_vega_lite()

    assert spec["usermeta"]["transform_contract"] == {"declared": ["density"]}

    inventory = collect_transform_inventory(spec)
    assert "density" in inventory.kinds
