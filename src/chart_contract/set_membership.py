"""Two-set membership summaries and schematic Venn layout helpers."""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral
from typing import Any

import pandas as pd


@dataclass(frozen=True, slots=True)
class SetMembershipSummary:
    """Counts for the four mutually exclusive regions of two sets."""

    a_only: int
    overlap: int
    b_only: int
    neither: int

    @property
    def total(self) -> int:
        return self.a_only + self.overlap + self.b_only + self.neither

    @property
    def a_total(self) -> int:
        return self.a_only + self.overlap

    @property
    def b_total(self) -> int:
        return self.b_only + self.overlap

    def to_dict(self) -> dict[str, int]:
        return {
            "a_only": self.a_only,
            "overlap": self.overlap,
            "b_only": self.b_only,
            "neither": self.neither,
            "a_total": self.a_total,
            "b_total": self.b_total,
            "total": self.total,
        }


def is_binary_membership_series(series: pd.Series) -> bool:
    """Return whether all values are non-null booleans or integer 0/1 values."""

    if series.isna().any():
        return False
    return all(_coerce_membership_value(value) is not None for value in series.tolist())


def membership_summary(data: pd.DataFrame, *, set_a: str, set_b: str) -> SetMembershipSummary:
    """Summarize two binary membership columns into mutually exclusive regions."""

    missing = [field for field in (set_a, set_b) if field not in data.columns]
    if missing:
        raise ValueError(f"Missing membership column(s): {', '.join(missing)}")
    if not is_binary_membership_series(data[set_a]) or not is_binary_membership_series(data[set_b]):
        raise ValueError("Set membership columns must contain only non-null booleans or integer 0/1 values.")

    in_a = data[set_a].map(_coerce_membership_value).astype(bool)
    in_b = data[set_b].map(_coerce_membership_value).astype(bool)
    return SetMembershipSummary(
        a_only=int((in_a & ~in_b).sum()),
        overlap=int((in_a & in_b).sum()),
        b_only=int((~in_a & in_b).sum()),
        neither=int((~in_a & ~in_b).sum()),
    )


def venn_layout_records(
    summary: SetMembershipSummary,
    *,
    set_a_label: str,
    set_b_label: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return circle, region-label, and note records for a schematic two-set view."""

    if summary.a_only == 0 and summary.b_only == 0 and summary.overlap > 0:
        circles = [
            {
                "set_key": "equal",
                "set_label": f"{set_a_label} = {set_b_label}",
                "x": 50,
                "y": 52,
                "size": 64000,
                "members": summary.overlap,
            }
        ]
        regions = [
            {"x": 50, "y": 52, "label": f"Both: {summary.overlap}"},
            {"x": 23, "y": 42, "label": f"{set_a_label} only: 0"},
            {"x": 77, "y": 42, "label": f"{set_b_label} only: 0"},
        ]
        names = [{"x": 50, "y": 84, "label": f"{set_a_label} = {set_b_label}"}]
    elif summary.a_only == 0 and summary.overlap > 0:
        circles = [
            {
                "set_key": "b",
                "set_label": set_b_label,
                "x": 50,
                "y": 52,
                "size": 76000,
                "members": summary.b_total,
            },
            {
                "set_key": "a",
                "set_label": set_a_label,
                "x": 50,
                "y": 52,
                "size": 30000,
                "members": summary.a_total,
            },
        ]
        regions = [
            {"x": 50, "y": 52, "label": f"Both: {summary.overlap}"},
            {"x": 68, "y": 52, "label": f"{set_b_label} only: {summary.b_only}"},
            {"x": 20, "y": 40, "label": f"{set_a_label} only: 0"},
        ]
        names = [
            {"x": 34, "y": 84, "label": set_a_label},
            {"x": 70, "y": 84, "label": set_b_label},
        ]
    elif summary.b_only == 0 and summary.overlap > 0:
        circles = [
            {
                "set_key": "a",
                "set_label": set_a_label,
                "x": 50,
                "y": 52,
                "size": 76000,
                "members": summary.a_total,
            },
            {
                "set_key": "b",
                "set_label": set_b_label,
                "x": 50,
                "y": 52,
                "size": 30000,
                "members": summary.b_total,
            },
        ]
        regions = [
            {"x": 50, "y": 52, "label": f"Both: {summary.overlap}"},
            {"x": 32, "y": 52, "label": f"{set_a_label} only: {summary.a_only}"},
            {"x": 80, "y": 40, "label": f"{set_b_label} only: 0"},
        ]
        names = [
            {"x": 30, "y": 84, "label": set_a_label},
            {"x": 66, "y": 84, "label": set_b_label},
        ]
    elif summary.overlap == 0:
        circles = [
            {
                "set_key": "a",
                "set_label": set_a_label,
                "x": 30,
                "y": 52,
                "size": 44000,
                "members": summary.a_total,
            },
            {
                "set_key": "b",
                "set_label": set_b_label,
                "x": 70,
                "y": 52,
                "size": 44000,
                "members": summary.b_total,
            },
        ]
        regions = [
            {"x": 30, "y": 52, "label": f"{set_a_label} only: {summary.a_only}"},
            {"x": 50, "y": 52, "label": "Overlap: 0"},
            {"x": 70, "y": 52, "label": f"{set_b_label} only: {summary.b_only}"},
        ]
        names = [
            {"x": 30, "y": 84, "label": set_a_label},
            {"x": 70, "y": 84, "label": set_b_label},
        ]
    else:
        circles = [
            {
                "set_key": "a",
                "set_label": set_a_label,
                "x": 40,
                "y": 52,
                "size": 56000,
                "members": summary.a_total,
            },
            {
                "set_key": "b",
                "set_label": set_b_label,
                "x": 60,
                "y": 52,
                "size": 56000,
                "members": summary.b_total,
            },
        ]
        regions = [
            {"x": 26, "y": 52, "label": f"{set_a_label} only: {summary.a_only}"},
            {"x": 50, "y": 52, "label": f"Both: {summary.overlap}"},
            {"x": 74, "y": 52, "label": f"{set_b_label} only: {summary.b_only}"},
        ]
        names = [
            {"x": 28, "y": 84, "label": set_a_label},
            {"x": 72, "y": 84, "label": set_b_label},
        ]

    names.extend(
        [
            {"x": 50, "y": 10, "label": f"Neither: {summary.neither} | Universe: {summary.total}"},
            {"x": 50, "y": 95, "label": "Schematic geometry; labeled region counts are authoritative."},
        ]
    )
    return circles, regions, names


def _coerce_membership_value(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, Integral) and value in (0, 1):
        return bool(value)
    return None
