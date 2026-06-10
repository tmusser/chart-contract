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
    x: str
    y: str
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

    def audit(self) -> AuditReport:
        return audit_chart(self)

    def to_altair(self) -> Any:
        from .renderers.altair import render_chart

        return render_chart(self)

    def to_vega_lite(self) -> dict[str, Any]:
        return self.to_altair().to_dict()
