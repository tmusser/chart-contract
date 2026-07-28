from __future__ import annotations

import pandas as pd

from chart_contract import Chart
from chart_contract.set_membership import membership_summary, venn_layout_records


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "customer_id": ["c1", "c2", "c3", "c4", "c5", "c6"],
            "email": [1, 1, 1, 0, 0, 0],
            "paid_search": [0, 1, 1, 1, 0, 0],
        }
    )


def _severities(report):
    return {finding.rule_id: finding.severity for finding in report.findings}


def test_membership_summary_counts_all_four_regions() -> None:
    summary = membership_summary(_frame(), set_a="email", set_b="paid_search")

    assert summary.to_dict() == {
        "a_only": 1,
        "overlap": 2,
        "b_only": 1,
        "neither": 2,
        "a_total": 3,
        "b_total": 3,
        "total": 6,
    }


def test_set_membership_chart_renders_labeled_schematic_venn() -> None:
    chart = Chart.set_membership(
        data=_frame(),
        member="customer_id",
        set_a="email",
        set_b="paid_search",
        set_a_label="Email",
        set_b_label="Paid search",
        claim="Email and paid search reach two of the same customers.",
        source="synthetic.channel_reach",
        title="Customer reach overlap by channel",
    )

    spec = chart.to_vega_lite()

    assert chart.intent == "set_membership"
    assert spec["layer"][0]["mark"]["type"] == "circle"
    assert spec["layer"][1]["mark"]["type"] == "text"
    assert spec["usermeta"]["chart_contract_intent"] == "set_membership"
    assert spec["usermeta"]["set_membership"]["region_counts"]["overlap"] == 2
    assert "schematic" in spec["usermeta"]["set_membership"]["area_semantics"]


def test_valid_set_membership_contract_is_ready() -> None:
    report = Chart.set_membership(
        data=_frame(),
        member="customer_id",
        set_a="email",
        set_b="paid_search",
        claim="Email and paid search reach two of the same customers.",
        source="synthetic.channel_reach",
        title="Customer reach overlap by channel",
    ).audit()

    assert report.verdict == "READY"
    assert _severities(report)["data.set_membership.binary"] == "PASS"
    assert _severities(report)["data.set_membership.member_unique"] == "PASS"
    assert _severities(report)["visual.set_membership.area_semantics"] == "PASS"


def test_set_membership_audit_blocks_non_binary_membership() -> None:
    frame = _frame()
    frame.loc[0, "email"] = 2

    report = Chart.set_membership(
        data=frame,
        member="customer_id",
        set_a="email",
        set_b="paid_search",
        claim="The channels overlap.",
        source="synthetic.channel_reach",
        title="Customer reach overlap by channel",
    ).audit()

    assert report.verdict == "BLOCK"
    assert _severities(report)["data.set_membership.binary"] == "FAIL"


def test_set_membership_audit_blocks_duplicate_members() -> None:
    frame = _frame()
    frame.loc[1, "customer_id"] = "c1"

    report = Chart.set_membership(
        data=frame,
        member="customer_id",
        set_a="email",
        set_b="paid_search",
        claim="The channels overlap.",
        source="synthetic.channel_reach",
        title="Customer reach overlap by channel",
    ).audit()

    assert report.verdict == "BLOCK"
    assert _severities(report)["data.set_membership.member_unique"] == "FAIL"


def test_disjoint_sets_use_separate_circle_positions() -> None:
    summary = membership_summary(
        pd.DataFrame({"a": [1, 1, 0, 0], "b": [0, 0, 1, 1]}),
        set_a="a",
        set_b="b",
    )

    circles, regions, _ = venn_layout_records(summary, set_a_label="A", set_b_label="B")

    assert [circle["x"] for circle in circles] == [30, 70]
    assert any(region["label"] == "Overlap: 0" for region in regions)


def test_subset_layout_nests_circles_at_the_same_center() -> None:
    summary = membership_summary(
        pd.DataFrame({"a": [1, 1, 0], "b": [1, 1, 1]}),
        set_a="a",
        set_b="b",
    )

    circles, _, _ = venn_layout_records(summary, set_a_label="A", set_b_label="B")

    assert [circle["x"] for circle in circles] == [50, 50]
    assert circles[0]["size"] > circles[1]["size"]


def test_generated_region_metadata_cannot_be_overridden() -> None:
    chart = Chart.set_membership(
        data=_frame(),
        member="customer_id",
        set_a="email",
        set_b="paid_search",
        claim="Email and paid search reach two of the same customers.",
        source="synthetic.channel_reach",
        title="Customer reach overlap by channel",
        metadata={
            "chart_contract_intent": "rank",
            "set_membership": {"region_counts": {"overlap": 999}},
        },
    )

    spec = chart.to_vega_lite()

    assert spec["usermeta"]["chart_contract_intent"] == "set_membership"
    assert spec["usermeta"]["set_membership"]["region_counts"]["overlap"] == 2
