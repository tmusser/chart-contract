from __future__ import annotations

from copy import deepcopy

import pandas as pd

from chart_contract import Chart, audit_spec


def _finding(report, rule_id: str):
    return next(f for f in report.findings if f.rule_id == rule_id)


def _chart(frame: pd.DataFrame, **overrides) -> Chart:
    kwargs = {
        "data": frame,
        "x": "period",
        "y": "active_users",
        "claim": "Observed active users differ across periods.",
        "source": "synthetic.metric_definition",
        "unit": "users",
        "title": "Observed active users",
        "metric_id": "monthly_active_users",
        "metric_definition": "Unique users with at least one qualifying session in the measurement window.",
        "metric_version": "v1",
        "metric_basis_field": "metric_version",
    }
    kwargs.update(overrides)
    return Chart.trend(**kwargs)


def test_stable_metric_definition_basis_passes() -> None:
    frame = pd.DataFrame(
        {
            "period": ["before", "after"],
            "active_users": [100, 120],
            "metric_version": ["v1", "v1"],
        }
    )

    report = _chart(frame).audit()

    assert _finding(report, "contract.metric.definition").severity == "PASS"
    assert _finding(report, "data.metric.definition_basis").severity == "PASS"
    assert report.verdict == "READY"


def test_first_party_spec_preserves_closed_metric_definition_contract() -> None:
    frame = pd.DataFrame(
        {
            "period": ["before", "after"],
            "active_users": [100, 120],
            "metric_version": ["v1", "v1"],
        }
    )

    spec = _chart(frame).to_vega_lite()

    assert spec["usermeta"]["metric_definition_contract"] == {
        "version": 1,
        "metric_field": "active_users",
        "metric_id": "monthly_active_users",
        "metric_definition": (
            "Unique users with at least one qualifying session in the measurement window."
        ),
        "metric_version": "v1",
        "metric_basis_field": "metric_version",
    }


def test_partial_metric_definition_contract_blocks() -> None:
    frame = pd.DataFrame(
        {
            "period": ["before", "after"],
            "active_users": [100, 120],
        }
    )
    chart = Chart.trend(
        data=frame,
        x="period",
        y="active_users",
        claim="Observed active users differ across periods.",
        source="synthetic.metric_definition",
        unit="users",
        title="Observed active users",
        metric_id="monthly_active_users",
    )

    report = chart.audit()

    assert _finding(report, "contract.metric.definition").severity == "FAIL"
    assert report.verdict == "BLOCK"


def test_mixed_row_level_metric_versions_block() -> None:
    frame = pd.DataFrame(
        {
            "period": ["before", "after"],
            "active_users": [100, 120],
            "metric_version": ["v1", "v2"],
        }
    )

    report = _chart(frame).audit()

    finding = _finding(report, "data.metric.definition_basis")
    assert finding.severity == "FAIL"
    assert "mixed metric versions" in finding.message
    assert report.verdict == "BLOCK"


def test_uniform_basis_must_match_declared_version() -> None:
    frame = pd.DataFrame(
        {
            "period": ["before", "after"],
            "active_users": [100, 120],
            "metric_version": ["v2", "v2"],
        }
    )

    report = _chart(frame).audit()

    finding = _finding(report, "data.metric.definition_basis")
    assert finding.severity == "FAIL"
    assert "declares version 'v2'" in finding.message


def test_null_or_missing_basis_blocks() -> None:
    null_frame = pd.DataFrame(
        {
            "period": ["before", "after"],
            "active_users": [100, 120],
            "metric_version": ["v1", None],
        }
    )
    missing_frame = pd.DataFrame(
        {
            "period": ["before", "after"],
            "active_users": [100, 120],
        }
    )

    assert _finding(
        _chart(null_frame).audit(),
        "data.metric.definition_basis",
    ).severity == "FAIL"
    assert _finding(
        _chart(missing_frame).audit(),
        "data.metric.definition_basis",
    ).severity == "FAIL"


def test_contract_without_basis_field_is_metadata_identity_only() -> None:
    frame = pd.DataFrame(
        {
            "period": ["before", "after"],
            "active_users": [100, 120],
        }
    )
    report = _chart(frame, metric_basis_field=None).audit()

    assert _finding(report, "contract.metric.definition").severity == "PASS"
    assert not any(
        f.rule_id == "data.metric.definition_basis" for f in report.findings
    )
    assert report.verdict == "READY"


def _external_spec() -> tuple[dict, pd.DataFrame]:
    frame = pd.DataFrame(
        {
            "period": ["before", "after"],
            "active_users": [100, 120],
            "metric_version": ["v1", "v1"],
        }
    )
    spec = {
        "mark": "line",
        "title": "Observed active users",
        "encoding": {
            "x": {"field": "period", "type": "ordinal"},
            "y": {"field": "active_users", "type": "quantitative"},
        },
        "usermeta": {
            "source": "synthetic.metric_definition",
            "unit": "users",
            "metric_definition_contract": {
                "version": 1,
                "metric_field": "active_users",
                "metric_id": "monthly_active_users",
                "metric_definition": (
                    "Unique users with at least one qualifying session in the measurement window."
                ),
                "metric_version": "v1",
                "metric_basis_field": "metric_version",
            },
        },
    }
    return spec, frame


def test_external_metric_definition_contract_passes() -> None:
    spec, frame = _external_spec()

    report = audit_spec(
        spec,
        data=frame,
        claim="Observed active users differ across periods.",
    )

    assert _finding(report, "contract.metric.definition").severity == "PASS"
    assert _finding(report, "data.metric.definition_basis").severity == "PASS"
    assert report.verdict == "READY"


def test_external_mixed_metric_versions_block() -> None:
    spec, frame = _external_spec()
    frame.loc[1, "metric_version"] = "v2"

    report = audit_spec(
        spec,
        data=frame,
        claim="Observed active users differ across periods.",
    )

    assert _finding(report, "data.metric.definition_basis").severity == "FAIL"
    assert report.verdict == "BLOCK"


def test_external_basis_requires_reconstructable_evidence() -> None:
    spec, _ = _external_spec()

    report = audit_spec(
        spec,
        data=None,
        claim="Observed active users differ across periods.",
    )

    assert _finding(report, "data.metric.definition_basis").severity == "FAIL"


def test_external_metric_field_must_bind_to_quantitative_encoding() -> None:
    spec, frame = _external_spec()
    spec["usermeta"]["metric_definition_contract"]["metric_field"] = "other_metric"

    report = audit_spec(
        spec,
        data=frame,
        claim="Observed active users differ across periods.",
    )

    assert _finding(report, "contract.metric.definition").severity == "FAIL"


def test_closed_metric_definition_schema_blocks_extra_fields() -> None:
    spec, frame = _external_spec()
    spec["usermeta"]["metric_definition_contract"]["owner"] = "analytics"

    report = audit_spec(
        spec,
        data=frame,
        claim="Observed active users differ across periods.",
    )

    assert _finding(report, "contract.metric.definition").severity == "FAIL"


def test_absent_metric_definition_contract_does_not_invent_identity() -> None:
    spec, frame = _external_spec()
    del spec["usermeta"]["metric_definition_contract"]

    report = audit_spec(
        spec,
        data=frame,
        claim="Observed active users differ across periods.",
    )

    assert not any(
        f.rule_id in {"contract.metric.definition", "data.metric.definition_basis"}
        for f in report.findings
    )
