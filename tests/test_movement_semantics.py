"""Deterministic regression tests for utility-neutral movement."""

import pytest

from chart_contract.directionality import movement_semantics


@pytest.mark.parametrize(
    ("baseline", "target"),
    [(100.0, 125.0), (125.0, 100.0)],
)
def test_neutral_movement_never_implies_improvement_or_worsening(
    baseline: float, target: float
) -> None:
    assert movement_semantics(baseline, target, direction="neutral") == "neutral"


@pytest.mark.parametrize(
    "direction",
    ["neutral", "higher_is_better", "lower_is_better"],
)
def test_unchanged_movement_is_unchanged_for_all_directions(direction: str) -> None:
    assert movement_semantics(100.0, 100.0, direction=direction) == "unchanged"
