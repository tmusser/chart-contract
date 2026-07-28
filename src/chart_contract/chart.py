"""Chart intent models and front-door API."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import pandas as pd

from .audit import AuditReport, audit_chart


@dataclass(slots=True)
class Chart:
    intent: str
    data: pd.DataFrame
    x: str | None = None
    y: str | None = None
    value: str | None = None
    bins: int | str | None = None
    distribution: str = "normal"
    category: str | None = None
    group: str | None = None
    claim: str = ""
    source: str | None = None
    unit: str | None = None
    title: str | None = None
    event: Mapping[str, Any] | None = None
    caveat: str | None = None
    filters: Mapping[str, Any] | str | None = None
    metadata: Mapping[str, Any] | None = None
    member: str | None = None
    set_a: str | None = None
    set_b: str | None = None
    set_a_label: str | None = None
    set_b_label: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.data, pd.DataFrame):
            self.data = pd.DataFrame(self.data)

    @classmethod
    def trend(
        cls,
        *,
        data: pd.DataFrame,
        x: str,
        y: str,
        claim: str,
        source: str | None = None,
        unit: str | None = None,
        title: str | None = None,
        event: Mapping[str, Any] | None = None,
        caveat: str | None = None,
        filters: Mapping[str, Any] | str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "Chart":
        return cls(
            intent="trend",
            data=data,
            x=x,
            y=y,
            claim=claim,
            source=source,
            unit=unit,
            title=title,
            event=event,
            caveat=caveat,
            filters=filters,
            metadata=metadata,
        )

    @classmethod
    def rank(
        cls,
        *,
        data: pd.DataFrame,
        x: str,
        y: str,
        claim: str,
        source: str | None = None,
        unit: str | None = None,
        title: str | None = None,
        caveat: str | None = None,
        filters: Mapping[str, Any] | str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "Chart":
        return cls(
            intent="rank",
            data=data,
            x=x,
            y=y,
            category=x,
            claim=claim,
            source=source,
            unit=unit,
            title=title,
            caveat=caveat,
            filters=filters,
            metadata=metadata,
        )

    @classmethod
    def compare(
        cls,
        *,
        data: pd.DataFrame,
        x: str,
        y: str,
        claim: str,
        group: str | None = None,
        source: str | None = None,
        unit: str | None = None,
        title: str | None = None,
        caveat: str | None = None,
        filters: Mapping[str, Any] | str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "Chart":
        return cls(
            intent="compare",
            data=data,
            x=x,
            y=y,
            category=x,
            group=group,
            claim=claim,
            source=source,
            unit=unit,
            title=title,
            caveat=caveat,
            filters=filters,
            metadata=metadata,
        )

    @classmethod
    def histogram(
        cls,
        *,
        data: pd.DataFrame,
        value: str,
        claim: str,
        source: str | None = None,
        unit: str | None = None,
        title: str | None = None,
        bins: int | str | None = None,
        group: str | None = None,
        caveat: str | None = None,
        filters: Mapping[str, Any] | str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "Chart":
        return cls(
            intent="histogram",
            data=data,
            value=value,
            bins=bins,
            group=group,
            claim=claim,
            source=source,
            unit=unit,
            title=title,
            caveat=caveat,
            filters=filters,
            metadata=metadata,
        )

    @classmethod
    def boxplot(
        cls,
        *,
        data: pd.DataFrame,
        x: str | None = None,
        y: str,
        claim: str,
        source: str | None = None,
        unit: str | None = None,
        title: str | None = None,
        group: str | None = None,
        caveat: str | None = None,
        filters: Mapping[str, Any] | str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "Chart":
        return cls(
            intent="boxplot",
            data=data,
            x=x,
            y=y,
            category=x or group,
            group=group,
            claim=claim,
            source=source,
            unit=unit,
            title=title,
            caveat=caveat,
            filters=filters,
            metadata=metadata,
        )

    @classmethod
    def violin(
        cls,
        *,
        data: pd.DataFrame,
        x: str | None = None,
        y: str,
        claim: str,
        source: str | None = None,
        unit: str | None = None,
        title: str | None = None,
        group: str | None = None,
        caveat: str | None = None,
        filters: Mapping[str, Any] | str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "Chart":
        return cls(
            intent="violin",
            data=data,
            x=x,
            y=y,
            category=x or group,
            group=group,
            claim=claim,
            source=source,
            unit=unit,
            title=title,
            caveat=caveat,
            filters=filters,
            metadata=metadata,
        )

    @classmethod
    def qq(
        cls,
        *,
        data: pd.DataFrame,
        value: str,
        claim: str,
        distribution: str = "normal",
        group: str | None = None,
        source: str | None = None,
        unit: str | None = None,
        title: str | None = None,
        caveat: str | None = None,
        filters: Mapping[str, Any] | str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "Chart":
        return cls(
            intent="qq",
            data=data,
            value=value,
            distribution=distribution,
            group=group,
            claim=claim,
            source=source,
            unit=unit,
            title=title,
            caveat=caveat,
            filters=filters,
            metadata=metadata,
        )

    @classmethod
    def ecdf(
        cls,
        *,
        data: pd.DataFrame,
        value: str,
        claim: str,
        group: str | None = None,
        source: str | None = None,
        unit: str | None = None,
        title: str | None = None,
        caveat: str | None = None,
        filters: Mapping[str, Any] | str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "Chart":
        return cls(
            intent="ecdf",
            data=data,
            value=value,
            group=group,
            claim=claim,
            source=source,
            unit=unit,
            title=title,
            caveat=caveat,
            filters=filters,
            metadata=metadata,
        )

    @classmethod
    def residual(
        cls,
        *,
        data: pd.DataFrame,
        fitted: str,
        residual: str,
        claim: str,
        group: str | None = None,
        source: str | None = None,
        unit: str | None = None,
        title: str | None = None,
        caveat: str | None = None,
        filters: Mapping[str, Any] | str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "Chart":
        return cls(
            intent="residual",
            data=data,
            x=fitted,
            y=residual,
            group=group,
            claim=claim,
            source=source,
            unit=unit,
            title=title,
            caveat=caveat,
            filters=filters,
            metadata=metadata,
        )

    @classmethod
    def set_membership(
        cls,
        *,
        data: pd.DataFrame,
        member: str,
        set_a: str,
        set_b: str,
        claim: str,
        set_a_label: str | None = None,
        set_b_label: str | None = None,
        source: str | None = None,
        title: str | None = None,
        caveat: str | None = None,
        filters: Mapping[str, Any] | str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "Chart":
        """Build an audited two-set membership chart from row-level evidence."""

        return cls(
            intent="set_membership",
            data=data,
            member=member,
            set_a=set_a,
            set_b=set_b,
            set_a_label=set_a_label,
            set_b_label=set_b_label,
            claim=claim,
            source=source,
            title=title,
            caveat=caveat,
            filters=filters,
            metadata=metadata,
        )

    def audit(self) -> AuditReport:
        if self.intent == "set_membership":
            from .set_membership_audit import audit_set_membership_chart

            return audit_set_membership_chart(self)
        if self.intent in {"qq", "ecdf", "residual"}:
            from .statistical_audit import audit_statistical_chart

            return audit_statistical_chart(self)
        return audit_chart(self)

    def to_altair(self) -> Any:
        from .renderers.altair import render_chart

        return render_chart(self)

    def to_vega_lite(self) -> dict[str, Any]:
        return self.to_altair().to_dict()
