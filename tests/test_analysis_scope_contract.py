from __future__ import annotations

import pandas as pd
import pytest

from chart_contract import Chart, audit_spec


def _finding(report, rule_id: str):
    return next(f for f in report.findings if f.rule_id == rule_id)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "period": ["before", "after"],
            "active_users": [100, 120],
            "analysis_scope": ["us_paid_v1", "us_paid_v1"],
        }
    )


def _chart(frame: pd.DataFrame, **overrides) -> Chart:
    kwargs = {
        "data": frame,
        "x": "period",
        "y": "active_users",
        "claim": "Observed active users changed.",
        "source": "synthetic.analysis_scope",
        "unit": "users",
        "title": "Observed active users",
        "scope_id": "us_paid_customers",
        "scope_definition": "Users with country=US and billing_status=paid.",
        "scope_version": "v1",
        "scope_basis_field": "analysis_scope",
        "scope_basis_value": "us_paid_v1",
    }
    kwargs.update(overrides)
    return Chart.trend(**kwargs)


def test_stable_scope_identity_passes() -> None:
    report = _chart(_frame()).audit()

    assert _finding(report, "contract.analysis_scope.identity").severity == "PASS"
    assert _finding(report, "data.analysis_scope.basis").severity == "PASS"
    assert report.verdict == "READY"


def test_first_party_spec_preserves_closed_scope_contract() -> None:
    spec = _chart(_frame()).to_vega_lite()

    assert spec["usermeta"]["analysis_scope_contract"] == {
        "version": 1,
        "scope_id": "us_paid_customers",
        "scope_definition": "Users with country=US and billing_status=paid.",
        "scope_version": "v1",
        "scope_basis_field": "analysis_scope",
        "scope_basis_value": "us_paid_v1",
    }


def test_mixed_scope_basis_blocks_and_refuses_render() -> None:
    frame = _frame()
    frame.loc[1, "analysis_scope"] = "all_customers_v1"
    chart = _chart(frame)

    report = chart.audit()

    finding = _finding(report, "data.analysis_scope.basis")
    assert finding.severity == "FAIL"
    assert "mixed analysis scopes" in finding.message
    assert report.verdict == "BLOCK"
    with pytest.raises(ValueError, match="mixed analysis scopes"):
        chart.to_vega_lite()


def test_uniform_scope_basis_mismatch_blocks() -> None:
    frame = _frame()
    frame["analysis_scope"] = "all_customers_v1"

    report = _chart(frame).audit()

    finding = _finding(report, "data.analysis_scope.basis")
    assert finding.severity == "FAIL"
    assert "expects" in finding.message


@pytest.mark.parametrize(
    "overrides",
    [
        {"scope_id": None},
        {"scope_definition": None},
        {"scope_version": None},
        {"scope_basis_field": None},
        {"scope_basis_value": None},
    ],
)
def test_partial_scope_contract_blocks(overrides) -> None:
    report = _chart(_frame(), **overrides).audit()

    assert _finding(report, "contract.analysis_scope.identity").severity == "FAIL"
    assert report.verdict == "BLOCK"


def test_metadata_only_scope_contract_is_ready() -> None:
    report = _chart(
        _frame().drop(columns=["analysis_scope"]),
        scope_basis_field=None,
        scope_basis_value=None,
    ).audit()

    assert _finding(report, "contract.analysis_scope.identity").severity == "PASS"
    assert not any(f.rule_id == "data.analysis_scope.basis" for f in report.findings)
    assert report.verdict == "READY"


def _external_spec() -> tuple[dict, pd.DataFrame]:
    frame = _frame()
    spec = {
        "mark": "line",
        "title": "Observed active users",
        "encoding": {
            "x": {"field": "period", "type": "ordinal"},
            "y": {"field": "active_users", "type": "quantitative"},
        },
        "usermeta": {
            "source": "synthetic.analysis_scope",
            "unit": "users",
            "analysis_scope_contract": {
                "version": 1,
                "scope_id": "us_paid_customers",
                "scope_definition": "Users with country=US and billing_status=paid.",
                "scope_version": "v1",
                "scope_basis_field": "analysis_scope",
                "scope_basis_value": "us_paid_v1",
            },
        },
    }
    return spec, frame


def test_external_scope_contract_passes() -> None:
    spec, frame = _external_spec()

    report = audit_spec(spec, data=frame, claim="Observed active users changed.")

    assert _finding(report, "contract.analysis_scope.identity").severity == "PASS"
    assert _finding(report, "data.analysis_scope.basis").severity == "PASS"
    assert report.verdict == "READY"


def test_external_scope_basis_requires_reconstructable_evidence() -> None:
    spec, _ = _external_spec()

    report = audit_spec(spec, data=None, claim="Observed active users changed.")

    assert _finding(report, "data.analysis_scope.basis").severity == "FAIL"
    assert report.verdict == "BLOCK"


def test_closed_scope_schema_blocks_extra_fields() -> None:
    spec, frame = _external_spec()
    spec["usermeta"]["analysis_scope_contract"]["sql"] = "country = 'US'"

    report = audit_spec(spec, data=frame, claim="Observed active users changed.")

    assert _finding(report, "contract.analysis_scope.identity").severity == "FAIL"


def test_absent_scope_contract_does_not_invent_scope_identity() -> None:
    spec, frame = _external_spec()
    del spec["usermeta"]["analysis_scope_contract"]

    report = audit_spec(spec, data=frame, claim="Observed active users changed.")

    assert not any(
        f.rule_id in {"contract.analysis_scope.identity", "data.analysis_scope.basis"}
        for f in report.findings
    )
