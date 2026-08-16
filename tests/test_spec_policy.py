import pandas as pd

from chart_contract import audit_spec


def _line_spec(*, usermeta=None, scale=None):
    spec = {
        "mark": "line",
        "title": "Observed conversion trend",
        "encoding": {
            "x": {"field": "week", "type": "ordinal"},
            "y": {"field": "conversion_rate", "type": "quantitative"},
        },
        "usermeta": {
            "source": "synthetic.conversion",
            "unit": "conversion rate",
            **(usermeta or {}),
        },
    }
    if scale is not None:
        spec["encoding"]["y"]["scale"] = scale
    return spec


def _data():
    return pd.DataFrame(
        {
            "week": ["W1", "W2", "W3"],
            "conversion_rate": [0.41, 0.42, 0.43],
        }
    )


def _severities(report):
    return {finding.rule_id: finding.severity for finding in report.findings}


def test_untouched_scale_defaults_pass_policy() -> None:
    report = audit_spec(
        spec=_line_spec(),
        data=_data(),
        claim="Observed conversion increased across the three weeks.",
    )

    severities = _severities(report)
    assert severities["scale.override.authorization"] == "PASS"
    assert severities["scale.normalization.authorization"] == "PASS"


def test_cut_line_scale_blocks_without_explicit_user_request() -> None:
    report = audit_spec(
        spec=_line_spec(scale={"domain": [0.40, 0.44]}),
        data=_data(),
        claim="Observed conversion increased across the three weeks.",
    )

    assert report.verdict == "BLOCK"
    assert _severities(report)["scale.override.authorization"] == "FAIL"


def test_cut_line_scale_can_pass_policy_when_user_requested() -> None:
    report = audit_spec(
        spec=_line_spec(
            scale={"domain": [0.40, 0.44]},
            usermeta={"user_requested_scale_override": True},
        ),
        data=_data(),
        claim="Observed conversion increased across the three weeks.",
    )

    assert _severities(report)["scale.override.authorization"] == "PASS"


def test_normalized_stack_blocks_without_explicit_user_request() -> None:
    spec = {
        "mark": "bar",
        "title": "Share by segment",
        "encoding": {
            "x": {"field": "segment", "type": "nominal"},
            "y": {
                "field": "value",
                "type": "quantitative",
                "aggregate": "sum",
                "stack": "normalize",
            },
            "color": {"field": "group", "type": "nominal"},
        },
        "usermeta": {"source": "synthetic.segment", "unit": "share"},
    }
    data = pd.DataFrame(
        {
            "segment": ["A", "A", "B", "B"],
            "group": ["x", "y", "x", "y"],
            "value": [2, 3, 4, 1],
        }
    )

    report = audit_spec(spec=spec, data=data, claim="The composition differs by segment.")

    assert report.verdict == "BLOCK"
    assert _severities(report)["scale.normalization.authorization"] == "FAIL"


def test_normalized_stack_passes_policy_when_user_requested() -> None:
    spec = {
        "mark": "bar",
        "title": "Share by segment",
        "encoding": {
            "x": {"field": "segment", "type": "nominal"},
            "y": {
                "field": "value",
                "type": "quantitative",
                "aggregate": "sum",
                "stack": "normalize",
            },
            "color": {"field": "group", "type": "nominal"},
        },
        "usermeta": {
            "source": "synthetic.segment",
            "unit": "share",
            "user_requested_normalization": True,
        },
    }
    data = pd.DataFrame(
        {
            "segment": ["A", "A", "B", "B"],
            "group": ["x", "y", "x", "y"],
            "value": [2, 3, 4, 1],
        }
    )

    report = audit_spec(spec=spec, data=data, claim="The composition differs by segment.")

    assert _severities(report)["scale.normalization.authorization"] == "PASS"


def test_truncated_bar_still_fails_even_when_user_requested() -> None:
    spec = {
        "mark": "bar",
        "title": "Revenue by segment",
        "encoding": {
            "x": {"field": "segment", "type": "nominal"},
            "y": {
                "field": "revenue",
                "type": "quantitative",
                "scale": {"zero": False},
            },
        },
        "usermeta": {
            "source": "synthetic.revenue",
            "unit": "dollars",
            "user_requested_scale_override": True,
        },
    }
    data = pd.DataFrame({"segment": ["A", "B"], "revenue": [100, 105]})

    report = audit_spec(spec=spec, data=data, claim="Segment B has higher revenue than segment A.")

    severities = _severities(report)
    assert report.verdict == "BLOCK"
    assert severities["scale.override.authorization"] == "PASS"
    assert severities["scale.bar.nonzero_baseline"] == "FAIL"


def test_explicit_bar_domain_excluding_zero_still_fails_when_user_requested() -> None:
    spec = {
        "mark": "bar",
        "title": "Revenue by segment",
        "encoding": {
            "x": {"field": "segment", "type": "nominal"},
            "y": {
                "field": "revenue",
                "type": "quantitative",
                "scale": {"domain": [100, 110]},
            },
        },
        "usermeta": {
            "source": "synthetic.revenue",
            "unit": "dollars",
            "user_requested_scale_override": True,
        },
    }
    data = pd.DataFrame({"segment": ["A", "B"], "revenue": [100, 105]})

    report = audit_spec(spec=spec, data=data, claim="Segment B has higher revenue than segment A.")

    severities = _severities(report)
    assert report.verdict == "BLOCK"
    assert severities["scale.override.authorization"] == "PASS"
    assert severities["scale.bar.explicit_domain_zero"] == "FAIL"
