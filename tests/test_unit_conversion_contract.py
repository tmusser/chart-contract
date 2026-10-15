from __future__ import annotations

from copy import deepcopy

import pandas as pd
import pytest

from chart_contract import Chart, audit_spec


def _finding(report, rule_id: str):
    return next(f for f in report.findings if f.rule_id == rule_id)


def _scale_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "period": ["before", "after"],
            "revenue_kusd": [1.0, 1.25],
            "revenue_usd": [1000.0, 1250.0],
            "source_unit": ["USD", "USD"],
        }
    )


def _scale_chart(frame: pd.DataFrame, **overrides) -> Chart:
    kwargs = {
        "data": frame,
        "x": "period",
        "y": "revenue_kusd",
        "claim": "Observed revenue differs across periods.",
        "source": "synthetic.unit_conversion",
        "unit": "thousand USD",
        "title": "Observed revenue",
        "source_unit": "USD",
        "conversion_kind": "scale",
        "conversion_factor": 0.001,
        "conversion_basis": "1 thousand USD = 1000 USD",
        "source_value_field": "revenue_usd",
        "source_unit_basis_field": "source_unit",
    }
    kwargs.update(overrides)
    return Chart.trend(**kwargs)


def test_fixed_scale_conversion_passes_and_recomputes() -> None:
    report = _scale_chart(_scale_frame()).audit()

    assert _finding(report, "contract.unit.conversion").severity == "PASS"
    assert _finding(report, "data.unit.source_basis").severity == "PASS"
    assert _finding(report, "data.unit.conversion_evidence").severity == "PASS"
    assert report.verdict == "READY"


def test_first_party_spec_preserves_closed_unit_conversion_contract() -> None:
    spec = _scale_chart(_scale_frame()).to_vega_lite()

    assert spec["usermeta"]["unit_conversion_contract"] == {
        "version": 1,
        "metric_field": "revenue_kusd",
        "source_unit": "USD",
        "display_unit": "thousand USD",
        "conversion_kind": "scale",
        "conversion_factor": 0.001,
        "conversion_basis": "1 thousand USD = 1000 USD",
        "source_value_field": "revenue_usd",
        "source_unit_basis_field": "source_unit",
    }


def test_stale_fixed_conversion_arithmetic_blocks_and_refuses_render() -> None:
    frame = _scale_frame()
    frame.loc[1, "revenue_kusd"] = 1.30
    chart = _scale_chart(frame)

    report = chart.audit()

    assert _finding(report, "data.unit.conversion_evidence").severity == "FAIL"
    assert report.verdict == "BLOCK"
    with pytest.raises(ValueError, match="disagrees"):
        chart.to_vega_lite()


def test_mixed_source_unit_basis_blocks() -> None:
    frame = _scale_frame()
    frame.loc[1, "source_unit"] = "EUR"

    report = _scale_chart(frame).audit()

    finding = _finding(report, "data.unit.source_basis")
    assert finding.severity == "FAIL"
    assert "mixed source units" in finding.message
    assert report.verdict == "BLOCK"


def test_identity_conversion_can_verify_row_unit_identity() -> None:
    frame = pd.DataFrame(
        {
            "period": ["before", "after"],
            "latency_seconds": [1.2, 1.0],
            "source_unit": ["seconds", "seconds"],
        }
    )
    chart = Chart.trend(
        data=frame,
        x="period",
        y="latency_seconds",
        claim="Observed latency differs across periods.",
        source="synthetic.latency",
        unit="seconds",
        title="Observed latency",
        source_unit="seconds",
        conversion_kind="identity",
        conversion_factor=1.0,
        source_unit_basis_field="source_unit",
    )

    report = chart.audit()

    assert _finding(report, "contract.unit.conversion").severity == "PASS"
    assert _finding(report, "data.unit.source_basis").severity == "PASS"
    assert not any(f.rule_id == "data.unit.conversion_evidence" for f in report.findings)
    assert report.verdict == "READY"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"conversion_kind": None}, "conversion_kind"),
        ({"conversion_factor": None}, "conversion_factor"),
        ({"conversion_basis": None}, "conversion_basis"),
        ({"source_value_field": None}, "source_value_field"),
        ({"unit": "USD"}, "different source and display units"),
    ],
)
def test_malformed_or_partial_scale_contract_blocks(overrides, message) -> None:
    report = _scale_chart(_scale_frame(), **overrides).audit()

    finding = _finding(report, "contract.unit.conversion")
    assert finding.severity == "FAIL"
    assert message in finding.message
    assert report.verdict == "BLOCK"


def _external_spec() -> tuple[dict, pd.DataFrame]:
    frame = _scale_frame()
    spec = {
        "mark": "line",
        "title": "Observed revenue",
        "encoding": {
            "x": {"field": "period", "type": "ordinal"},
            "y": {"field": "revenue_kusd", "type": "quantitative"},
        },
        "usermeta": {
            "source": "synthetic.unit_conversion",
            "unit": "thousand USD",
            "unit_conversion_contract": {
                "version": 1,
                "metric_field": "revenue_kusd",
                "source_unit": "USD",
                "display_unit": "thousand USD",
                "conversion_kind": "scale",
                "conversion_factor": 0.001,
                "conversion_basis": "1 thousand USD = 1000 USD",
                "source_value_field": "revenue_usd",
                "source_unit_basis_field": "source_unit",
            },
        },
    }
    return spec, frame


def test_external_fixed_conversion_passes() -> None:
    spec, frame = _external_spec()
    report = audit_spec(spec, data=frame, claim="Observed revenue differs across periods.")

    assert _finding(report, "contract.unit.conversion").severity == "PASS"
    assert _finding(report, "data.unit.source_basis").severity == "PASS"
    assert _finding(report, "data.unit.conversion_evidence").severity == "PASS"
    assert report.verdict == "READY"


def test_external_display_unit_mismatch_blocks() -> None:
    spec, frame = _external_spec()
    spec["usermeta"]["unit"] = "USD"

    report = audit_spec(spec, data=frame, claim="Observed revenue differs across periods.")

    assert _finding(report, "contract.unit.conversion").severity == "FAIL"
    assert report.verdict == "BLOCK"


def test_external_scale_requires_reconstructable_evidence() -> None:
    spec, _ = _external_spec()

    report = audit_spec(spec, data=None, claim="Observed revenue differs across periods.")

    assert _finding(report, "data.unit.conversion_evidence").severity == "FAIL"


def test_external_metric_field_must_bind_to_quantitative_encoding() -> None:
    spec, frame = _external_spec()
    spec["usermeta"]["unit_conversion_contract"]["metric_field"] = "other"

    report = audit_spec(spec, data=frame, claim="Observed revenue differs across periods.")

    assert _finding(report, "contract.unit.conversion").severity == "FAIL"


def test_closed_unit_conversion_schema_blocks_extra_fields() -> None:
    spec, frame = _external_spec()
    spec["usermeta"]["unit_conversion_contract"]["fx_provider"] = "example"

    report = audit_spec(spec, data=frame, claim="Observed revenue differs across periods.")

    assert _finding(report, "contract.unit.conversion").severity == "FAIL"


def test_absent_unit_conversion_contract_does_not_invent_conversion() -> None:
    spec, frame = _external_spec()
    del spec["usermeta"]["unit_conversion_contract"]

    report = audit_spec(spec, data=frame, claim="Observed revenue differs across periods.")

    assert not any(
        f.rule_id in {
            "contract.unit.conversion",
            "data.unit.source_basis",
            "data.unit.conversion_evidence",
        }
        for f in report.findings
    )
