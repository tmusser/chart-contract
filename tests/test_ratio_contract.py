from __future__ import annotations

import pandas as pd

from chart_contract import Chart, audit_spec


def _severity(report, rule_id: str) -> str:
    return next(finding.severity for finding in report.findings if finding.rule_id == rule_id)


def _trend(**kwargs) -> Chart:
    params = {
        "data": pd.DataFrame(
            {
                "week": ["W1", "W2", "W3"],
                "conversion_rate": [0.12, 0.14, 0.16],
            }
        ),
        "x": "week",
        "y": "conversion_rate",
        "claim": "Observed conversion rate increased across the measured weeks.",
        "source": "synthetic.funnel",
        "unit": "conversion rate",
        "title": "Weekly conversion rate",
    }
    params.update(kwargs)
    return Chart.trend(**params)


def test_distribution_intents_do_not_inherit_metric_ratio_requirement() -> None:
    chart = Chart.histogram(
        data=pd.DataFrame({"conversion_rate": [0.10, 0.20, 0.30, 0.40, 0.50]}),
        value="conversion_rate",
        claim="Observed conversion-rate distribution.",
        source="synthetic.funnel",
        unit="percent",
        value_representation="fraction",
        title="Conversion-rate distribution",
    )

    report = chart.audit()
    spec = chart.to_vega_lite()

    assert all(
        finding.rule_id != "contract.ratio.denominator"
        for finding in report.findings
    )
    assert "ratio_contract" not in spec.get("usermeta", {})


def test_ratio_like_metric_without_denominator_requires_review() -> None:
    report = _trend().audit()

    assert _severity(report, "contract.ratio.denominator") == "WARN"
    assert report.verdict == "REVIEW"


def test_explicit_numerator_denominator_contract_is_ready() -> None:
    report = _trend(
        numerator="converted_sessions",
        denominator="eligible_sessions",
        cohort="eligible onboarding sessions",
    ).audit()

    assert _severity(report, "contract.ratio.denominator") == "PASS"
    assert report.verdict == "READY"


def test_partial_ratio_contract_blocks() -> None:
    report = _trend(numerator="converted_sessions").audit()

    assert _severity(report, "contract.ratio.denominator") == "FAIL"
    assert report.verdict == "BLOCK"


def test_first_party_spec_preserves_ratio_contract() -> None:
    spec = _trend(
        numerator="converted_sessions",
        denominator="eligible_sessions",
        cohort="eligible onboarding sessions",
    ).to_vega_lite()

    assert spec["usermeta"]["ratio_contract"] == {
        "version": 1,
        "metric_field": "conversion_rate",
        "numerator": "converted_sessions",
        "denominator": "eligible_sessions",
        "cohort": "eligible onboarding sessions",
        "denominator_basis_field": None,
    }


def test_consistent_denominator_basis_field_passes() -> None:
    frame = pd.DataFrame(
        {
            "segment": ["SMB", "Enterprise"],
            "conversion_rate": [0.10, 0.20],
            "denominator_basis": ["eligible_sessions", "eligible_sessions"],
        }
    )
    chart = Chart.compare(
        data=frame,
        x="segment",
        y="conversion_rate",
        claim="Enterprise has the higher observed conversion rate.",
        source="synthetic.funnel",
        unit="conversion rate",
        title="Segment conversion rate",
        numerator="converted_sessions",
        denominator="eligible_sessions",
        denominator_basis_field="denominator_basis",
    )

    report = chart.audit()

    assert _severity(report, "contract.ratio.denominator") == "PASS"
    assert _severity(report, "data.ratio.denominator_basis") == "PASS"
    assert report.verdict == "READY"


def test_mixed_denominator_basis_blocks_comparison() -> None:
    frame = pd.DataFrame(
        {
            "segment": ["SMB", "Enterprise"],
            "conversion_rate": [0.10, 0.20],
            "denominator_basis": ["visitors", "signups"],
        }
    )
    chart = Chart.compare(
        data=frame,
        x="segment",
        y="conversion_rate",
        claim="Enterprise has the higher observed conversion rate.",
        source="synthetic.funnel",
        unit="conversion rate",
        title="Segment conversion rate",
        numerator="converted_users",
        denominator="visitors",
        denominator_basis_field="denominator_basis",
    )

    report = chart.audit()
    finding = next(
        finding
        for finding in report.findings
        if finding.rule_id == "data.ratio.denominator_basis"
    )

    assert finding.severity == "FAIL"
    assert "mixed denominator identities" in finding.message
    assert report.verdict == "BLOCK"


def test_basis_field_must_match_declared_denominator() -> None:
    frame = pd.DataFrame(
        {
            "segment": ["SMB", "Enterprise"],
            "conversion_rate": [0.10, 0.20],
            "denominator_basis": ["signups", "signups"],
        }
    )
    chart = Chart.compare(
        data=frame,
        x="segment",
        y="conversion_rate",
        claim="Enterprise has the higher observed conversion rate.",
        source="synthetic.funnel",
        unit="conversion rate",
        title="Segment conversion rate",
        numerator="converted_users",
        denominator="visitors",
        denominator_basis_field="denominator_basis",
    )

    report = chart.audit()

    assert _severity(report, "data.ratio.denominator_basis") == "FAIL"
    assert report.verdict == "BLOCK"


def test_null_denominator_basis_blocks() -> None:
    frame = pd.DataFrame(
        {
            "segment": ["SMB", "Enterprise"],
            "conversion_rate": [0.10, 0.20],
            "denominator_basis": ["visitors", None],
        }
    )
    chart = Chart.compare(
        data=frame,
        x="segment",
        y="conversion_rate",
        claim="Enterprise has the higher observed conversion rate.",
        source="synthetic.funnel",
        unit="conversion rate",
        title="Segment conversion rate",
        numerator="converted_users",
        denominator="visitors",
        denominator_basis_field="denominator_basis",
    )

    report = chart.audit()

    assert _severity(report, "data.ratio.denominator_basis") == "FAIL"


def test_explicit_ratio_contract_can_define_semantics_for_nonstandard_unit() -> None:
    chart = Chart.compare(
        data=pd.DataFrame({"segment": ["A", "B"], "metric": [2.1, 2.4]}),
        x="segment",
        y="metric",
        claim="B has the higher observed metric.",
        source="synthetic.metric",
        unit="events per thousand sessions",
        title="Events per thousand sessions",
        numerator="events",
        denominator="thousand_sessions",
    )

    report = chart.audit()

    assert _severity(report, "contract.ratio.denominator") == "PASS"
    assert report.verdict == "READY"


def _spec() -> dict:
    return {
        "mark": "bar",
        "title": "Segment conversion rate",
        "encoding": {
            "x": {"field": "segment", "type": "nominal"},
            "y": {
                "field": "conversion_rate",
                "type": "quantitative",
                "scale": {"zero": True},
            },
        },
        "usermeta": {
            "source": "synthetic.funnel",
            "unit": "conversion rate",
            "ratio_contract": {
                "version": 1,
                "metric_field": "conversion_rate",
                "numerator": "converted_users",
                "denominator": "visitors",
                "cohort": None,
                "denominator_basis_field": "denominator_basis",
            },
        },
    }


def test_external_ratio_spec_with_consistent_basis_passes() -> None:
    spec = _spec()
    data = pd.DataFrame(
        {
            "segment": ["SMB", "Enterprise"],
            "conversion_rate": [0.10, 0.20],
            "denominator_basis": ["visitors", "visitors"],
        }
    )

    report = audit_spec(
        spec=spec,
        data=data,
        claim="Enterprise has the higher observed conversion rate.",
    )

    assert _severity(report, "contract.ratio.denominator") == "PASS"
    assert _severity(report, "data.ratio.denominator_basis") == "PASS"
    assert report.verdict == "READY"


def test_external_ratio_spec_with_mixed_basis_blocks() -> None:
    spec = _spec()
    data = pd.DataFrame(
        {
            "segment": ["SMB", "Enterprise"],
            "conversion_rate": [0.10, 0.20],
            "denominator_basis": ["visitors", "signups"],
        }
    )

    report = audit_spec(
        spec=spec,
        data=data,
        claim="Enterprise has the higher observed conversion rate.",
    )

    assert _severity(report, "data.ratio.denominator_basis") == "FAIL"
    assert report.verdict == "BLOCK"


def test_external_ratio_spec_metric_binding_must_match_quantitative_encoding() -> None:
    spec = _spec()
    spec["usermeta"]["ratio_contract"]["metric_field"] = "other_rate"
    data = pd.DataFrame(
        {
            "segment": ["SMB", "Enterprise"],
            "conversion_rate": [0.10, 0.20],
            "denominator_basis": ["visitors", "visitors"],
        }
    )

    report = audit_spec(
        spec=spec,
        data=data,
        claim="Enterprise has the higher observed conversion rate.",
    )

    assert _severity(report, "contract.ratio.denominator") == "FAIL"
    assert report.verdict == "BLOCK"


def test_external_ratio_spec_missing_contract_warns() -> None:
    spec = _spec()
    del spec["usermeta"]["ratio_contract"]
    data = pd.DataFrame(
        {
            "segment": ["SMB", "Enterprise"],
            "conversion_rate": [0.10, 0.20],
        }
    )

    report = audit_spec(
        spec=spec,
        data=data,
        claim="Enterprise has the higher observed conversion rate.",
    )

    assert _severity(report, "contract.ratio.denominator") == "WARN"
    assert report.verdict == "REVIEW"


def test_basis_field_declaration_requires_reconstructable_evidence() -> None:
    spec = _spec()

    report = audit_spec(
        spec=spec,
        data=None,
        claim="Enterprise has the higher observed conversion rate.",
    )

    assert _severity(report, "data.ratio.denominator_basis") == "FAIL"
    assert report.verdict == "BLOCK"


def test_closed_ratio_contract_schema_blocks_extra_fields() -> None:
    spec = _spec()
    spec["usermeta"]["ratio_contract"]["denominator_description"] = "Visitors to the site."
    data = pd.DataFrame(
        {
            "segment": ["SMB", "Enterprise"],
            "conversion_rate": [0.10, 0.20],
            "denominator_basis": ["visitors", "visitors"],
        }
    )

    report = audit_spec(
        spec=spec,
        data=data,
        claim="Enterprise has the higher observed conversion rate.",
    )

    assert _severity(report, "contract.ratio.denominator") == "FAIL"
    assert report.verdict == "BLOCK"
