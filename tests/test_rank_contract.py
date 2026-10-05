from __future__ import annotations

from copy import deepcopy

import pandas as pd
import pytest

from chart_contract import Chart, audit_spec, build_transform_lineage


def _frame(values: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "segment": [f"S{index + 1}" for index in range(len(values))],
            "score": values,
        }
    )


def _chart(frame: pd.DataFrame, *, top_n: int | None = None) -> Chart:
    return Chart.rank(
        data=frame,
        x="segment",
        y="score",
        top_n=top_n,
        claim="Segments are ranked by observed score.",
        source="synthetic.rank",
        unit="points",
        title="Observed segment ranking",
    )


def _finding(report, rule_id: str):
    return next(finding for finding in report.findings if finding.rule_id == rule_id)


def _dataset_rows(spec: dict) -> list[dict]:
    datasets = spec.get("datasets", {})
    assert len(datasets) == 1
    return next(iter(datasets.values()))


def test_full_rank_audit_and_renderer_declare_no_omissions() -> None:
    frame = _frame([5, 9, 7, 2])
    chart = _chart(frame)

    report = chart.audit()
    spec = chart.to_vega_lite()
    contract = spec["usermeta"]["rank_contract"]

    assert _finding(report, "data.rank.category_unique").severity == "PASS"
    assert _finding(report, "contract.rank.top_n").severity == "PASS"
    assert _finding(report, "contract.rank.truncation").severity == "PASS"
    assert _finding(report, "data.rank.cutoff_tie").severity == "PASS"
    assert _finding(report, "visual.rank.sort_order").severity == "PASS"
    assert contract == {
        "version": 1,
        "category_field": "segment",
        "metric_field": "score",
        "order": "descending",
        "top_n": None,
        "tie_policy": "include_cutoff_ties",
        "eligible_category_count": 4,
        "displayed_category_count": 4,
        "omitted_category_count": 0,
        "cutoff_tie_expanded": False,
    }
    assert spec["encoding"]["y"]["sort"] == ["S2", "S3", "S1", "S4"]
    assert "transform" not in spec
    assert len(_dataset_rows(spec)) == len(frame)


def test_top_n_keeps_full_source_rows_and_declares_omitted_categories() -> None:
    frame = _frame([10, 8, 6, 4, 2])
    chart = _chart(frame, top_n=3)

    report = chart.audit()
    spec = chart.to_vega_lite()
    contract = spec["usermeta"]["rank_contract"]

    assert report.verdict == "READY"
    assert contract["eligible_category_count"] == 5
    assert contract["displayed_category_count"] == 3
    assert contract["omitted_category_count"] == 2
    assert contract["top_n"] == 3
    assert len(_dataset_rows(spec)) == 5
    assert spec["transform"] == [
        {"filter": {"field": "segment", "oneOf": ["S1", "S2", "S3"]}}
    ]
    assert spec["encoding"]["y"]["sort"] == ["S1", "S2", "S3"]
    assert spec["usermeta"]["transform_contract"] == {"declared": ["filter"]}
    assert spec["usermeta"]["transform_lineage"] == build_transform_lineage(spec)

    spec_report = audit_spec(
        spec=spec,
        data=frame,
        claim="Segments are ranked by observed score.",
    )
    assert _finding(spec_report, "contract.rank.truncation").severity == "PASS"
    assert _finding(spec_report, "visual.rank.sort_order").severity == "PASS"
    assert spec_report.verdict == "READY"


def test_cutoff_ties_expand_display_instead_of_breaking_equal_values() -> None:
    frame = _frame([10, 9, 9, 5])
    chart = _chart(frame, top_n=2)

    report = chart.audit()
    spec = chart.to_vega_lite()
    contract = spec["usermeta"]["rank_contract"]

    assert contract["top_n"] == 2
    assert contract["displayed_category_count"] == 3
    assert contract["omitted_category_count"] == 1
    assert contract["cutoff_tie_expanded"] is True
    assert spec["transform"][0]["filter"]["oneOf"] == ["S1", "S2", "S3"]
    assert _finding(report, "data.rank.cutoff_tie").severity == "WARN"
    assert report.verdict == "REVIEW"

    spec_report = audit_spec(
        spec=spec,
        data=frame,
        claim="Segments are ranked by observed score.",
    )
    assert _finding(spec_report, "data.rank.cutoff_tie").severity == "WARN"
    assert spec_report.verdict == "REVIEW"


def test_rank_order_preserves_large_integer_precision() -> None:
    frame = pd.DataFrame(
        {
            "segment": ["A", "B", "C"],
            "score": [2**60, 2**60 + 1, 2**60 - 1],
        }
    )

    spec = _chart(frame).to_vega_lite()

    assert spec["encoding"]["y"]["sort"] == ["B", "A", "C"]


def test_equal_metrics_have_deterministic_display_order_without_false_rank_separation() -> None:
    frame = pd.DataFrame(
        {
            "segment": ["Beta", "Alpha", "Gamma"],
            "score": [10, 10, 8],
        }
    )

    spec = _chart(frame).to_vega_lite()

    assert spec["encoding"]["y"]["sort"] == ["Alpha", "Beta", "Gamma"]
    assert spec["usermeta"]["rank_contract"]["tie_policy"] == "include_cutoff_ties"


def test_duplicate_categories_block_rank_audit() -> None:
    frame = pd.DataFrame(
        {
            "segment": ["A", "A", "B"],
            "score": [10, 9, 8],
        }
    )

    report = _chart(frame).audit()

    assert report.verdict == "BLOCK"
    assert _finding(report, "data.rank.category_unique").severity == "FAIL"


def test_top_n_render_refuses_duplicate_categories_instead_of_silently_aggregating() -> None:
    frame = pd.DataFrame(
        {
            "segment": ["A", "A", "B"],
            "score": [10, 9, 8],
        }
    )

    with pytest.raises(ValueError, match="one row per non-null category"):
        _chart(frame, top_n=2).to_vega_lite()


@pytest.mark.parametrize("top_n", [0, -1, True, 2.5])
def test_invalid_top_n_blocks_and_cannot_render(top_n) -> None:
    chart = _chart(_frame([5, 4, 3]), top_n=top_n)

    report = chart.audit()

    assert report.verdict == "BLOCK"
    assert _finding(report, "contract.rank.top_n").severity == "FAIL"
    with pytest.raises(ValueError, match="positive integer"):
        chart.to_vega_lite()


def test_explicit_top_n_controls_readability_on_displayed_not_source_count() -> None:
    frame = _frame(list(range(20, 0, -1)))

    full_report = _chart(frame).audit()
    top_report = _chart(frame, top_n=8).audit()

    assert _finding(full_report, "readability.rank.category_count").severity == "WARN"
    assert _finding(top_report, "readability.rank.category_count").severity == "PASS"


def test_rank_spec_blocks_sort_tampering() -> None:
    frame = _frame([10, 8, 6, 4])
    spec = _chart(frame).to_vega_lite()
    spec["encoding"]["y"]["sort"] = list(reversed(spec["encoding"]["y"]["sort"]))

    report = audit_spec(
        spec=spec,
        data=frame,
        claim="Segments are ranked by observed score.",
    )

    assert report.verdict == "BLOCK"
    assert _finding(report, "visual.rank.sort_order").severity == "FAIL"


def test_rank_spec_blocks_wrong_top_n_filter_even_with_fresh_transform_receipt() -> None:
    frame = _frame([10, 8, 6, 4, 2])
    spec = _chart(frame, top_n=3).to_vega_lite()
    spec["transform"][0]["filter"]["oneOf"] = ["S1", "S2", "S4"]
    spec["usermeta"]["transform_lineage"] = build_transform_lineage(spec)

    report = audit_spec(
        spec=spec,
        data=frame,
        claim="Segments are ranked by observed score.",
    )
    truncation_findings = [
        finding
        for finding in report.findings
        if finding.rule_id == "contract.rank.truncation"
    ]

    assert report.verdict == "BLOCK"
    assert any(
        finding.severity == "FAIL" and "top-N category set" in finding.message
        for finding in truncation_findings
    )


def test_rank_spec_blocks_count_metadata_drift() -> None:
    frame = _frame([10, 8, 6, 4, 2])
    spec = _chart(frame, top_n=3).to_vega_lite()
    spec["usermeta"]["rank_contract"]["eligible_category_count"] = 6
    spec["usermeta"]["rank_contract"]["omitted_category_count"] = 3

    report = audit_spec(
        spec=spec,
        data=frame,
        claim="Segments are ranked by observed score.",
    )

    assert report.verdict == "BLOCK"
    assert any(
        finding.severity == "FAIL"
        for finding in report.findings
        if finding.rule_id == "contract.rank.truncation"
    )


def test_opt_in_rank_spec_without_rank_contract_blocks() -> None:
    frame = _frame([10, 8, 6])
    spec = {
        "mark": "bar",
        "title": "Observed segment ranking",
        "encoding": {
            "x": {"field": "score", "type": "quantitative"},
            "y": {"field": "segment", "type": "nominal", "sort": ["S1", "S2", "S3"]},
        },
        "usermeta": {
            "chart_contract_intent": "rank",
            "source": "synthetic.rank",
            "unit": "points",
        },
    }

    report = audit_spec(
        spec=spec,
        data=frame,
        claim="Segments are ranked by observed score.",
    )

    assert report.verdict == "BLOCK"
    assert _finding(report, "contract.rank.truncation").severity == "FAIL"


def test_rank_spec_blocks_duplicate_source_categories() -> None:
    frame = pd.DataFrame(
        {
            "segment": ["A", "A", "B"],
            "score": [10, 9, 8],
        }
    )
    spec = {
        "mark": "bar",
        "title": "Observed segment ranking",
        "encoding": {
            "x": {"field": "score", "type": "quantitative"},
            "y": {"field": "segment", "type": "nominal", "sort": ["A", "B"]},
        },
        "usermeta": {
            "chart_contract_intent": "rank",
            "source": "synthetic.rank",
            "unit": "points",
            "rank_contract": {
                "version": 1,
                "category_field": "segment",
                "metric_field": "score",
                "order": "descending",
                "top_n": None,
                "tie_policy": "include_cutoff_ties",
                "eligible_category_count": 2,
                "displayed_category_count": 2,
                "omitted_category_count": 0,
                "cutoff_tie_expanded": False,
            },
        },
    }

    report = audit_spec(
        spec=spec,
        data=frame,
        claim="Segments are ranked by observed score.",
    )

    assert report.verdict == "BLOCK"
    assert _finding(report, "data.rank.category_unique").severity == "FAIL"
