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
    value_representation: str | None = None
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
    node: str | None = None
    parent: str | None = None
    label: str | None = None
    branch: str | None = None
    top_n: int | None = None
    omitted_behavior: str | None = None
    other_label: str = "Other"
    numerator: str | None = None
    denominator: str | None = None
    cohort: str | None = None
    denominator_basis_field: str | None = None
    baseline_field: str | None = None
    baseline_value: str | int | float | None = None
    target_value: str | int | float | None = None
    change_type: str | None = None
    declared_change: float | int | None = None
    window_kind: str | None = None
    window_granularity: str | None = None
    baseline_start: str | None = None
    baseline_end: str | None = None
    target_start: str | None = None
    target_end: str | None = None
    baseline_complete: bool | None = None
    target_complete: bool | None = None
    grain_fields: tuple[str, ...] | list[str] | None = None
    metric_id: str | None = None
    metric_definition: str | None = None
    metric_version: str | None = None
    metric_basis_field: str | None = None
    source_unit: str | None = None
    conversion_kind: str | None = None
    conversion_factor: float | int | None = None
    conversion_basis: str | None = None
    source_value_field: str | None = None
    source_unit_basis_field: str | None = None
    evidence_scope: str | None = None
    population: str | None = None
    population_size: int | None = None
    sample_size: int | None = None
    sampling_method: str | None = None
    sample_member_field: str | None = None
    weight_field: str | None = None
    generalizes_to_population: bool | None = None
    interval_lower_field: str | None = None
    interval_upper_field: str | None = None
    interval_kind: str | None = None
    interval_level: float | int | None = None
    interval_method: str | None = None
    control_total: float | int | None = None
    control_total_source: str | None = None
    reconciliation_tolerance: float | int | None = None
    metric_direction: str | None = None

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
        value_representation: str | None = None,
        title: str | None = None,
        grain_fields: tuple[str, ...] | list[str] | None = None,
        metric_id: str | None = None,
        metric_definition: str | None = None,
        metric_version: str | None = None,
        metric_basis_field: str | None = None,
        source_unit: str | None = None,
        conversion_kind: str | None = None,
        conversion_factor: float | int | None = None,
        conversion_basis: str | None = None,
        source_value_field: str | None = None,
        source_unit_basis_field: str | None = None,
        evidence_scope: str | None = None,
        population: str | None = None,
        population_size: int | None = None,
        sample_size: int | None = None,
        sampling_method: str | None = None,
        sample_member_field: str | None = None,
        weight_field: str | None = None,
        generalizes_to_population: bool | None = None,
        interval_lower_field: str | None = None,
        interval_upper_field: str | None = None,
        interval_kind: str | None = None,
        interval_level: float | int | None = None,
        interval_method: str | None = None,
        metric_direction: str | None = None,
        numerator: str | None = None,
        denominator: str | None = None,
        cohort: str | None = None,
        denominator_basis_field: str | None = None,
        baseline_field: str | None = None,
        baseline_value: str | int | float | None = None,
        target_value: str | int | float | None = None,
        change_type: str | None = None,
        declared_change: float | int | None = None,
        window_kind: str | None = None,
        window_granularity: str | None = None,
        baseline_start: str | None = None,
        baseline_end: str | None = None,
        target_start: str | None = None,
        target_end: str | None = None,
        baseline_complete: bool | None = None,
        target_complete: bool | None = None,
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
            value_representation=value_representation,
            title=title,
            grain_fields=grain_fields,
            metric_id=metric_id,
            metric_definition=metric_definition,
            metric_version=metric_version,
            metric_basis_field=metric_basis_field,
            source_unit=source_unit,
            conversion_kind=conversion_kind,
            conversion_factor=conversion_factor,
            conversion_basis=conversion_basis,
            source_value_field=source_value_field,
            source_unit_basis_field=source_unit_basis_field,
            evidence_scope=evidence_scope,
            population=population,
            population_size=population_size,
            sample_size=sample_size,
            sampling_method=sampling_method,
            sample_member_field=sample_member_field,
            weight_field=weight_field,
            generalizes_to_population=generalizes_to_population,
            interval_lower_field=interval_lower_field,
            interval_upper_field=interval_upper_field,
            interval_kind=interval_kind,
            interval_level=interval_level,
            interval_method=interval_method,
            metric_direction=metric_direction,
            numerator=numerator,
            denominator=denominator,
            cohort=cohort,
            denominator_basis_field=denominator_basis_field,
            baseline_field=baseline_field,
            baseline_value=baseline_value,
            target_value=target_value,
            change_type=change_type,
            declared_change=declared_change,
            window_kind=window_kind,
            window_granularity=window_granularity,
            baseline_start=baseline_start,
            baseline_end=baseline_end,
            target_start=target_start,
            target_end=target_end,
            baseline_complete=baseline_complete,
            target_complete=target_complete,
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
        value_representation: str | None = None,
        title: str | None = None,
        grain_fields: tuple[str, ...] | list[str] | None = None,
        metric_id: str | None = None,
        metric_definition: str | None = None,
        metric_version: str | None = None,
        metric_basis_field: str | None = None,
        source_unit: str | None = None,
        conversion_kind: str | None = None,
        conversion_factor: float | int | None = None,
        conversion_basis: str | None = None,
        source_value_field: str | None = None,
        source_unit_basis_field: str | None = None,
        evidence_scope: str | None = None,
        population: str | None = None,
        population_size: int | None = None,
        sample_size: int | None = None,
        sampling_method: str | None = None,
        sample_member_field: str | None = None,
        weight_field: str | None = None,
        generalizes_to_population: bool | None = None,
        control_total: float | int | None = None,
        control_total_source: str | None = None,
        reconciliation_tolerance: float | int | None = None,
        numerator: str | None = None,
        denominator: str | None = None,
        cohort: str | None = None,
        denominator_basis_field: str | None = None,
        top_n: int | None = None,
        omitted_behavior: str | None = None,
        other_label: str = "Other",
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
            value_representation=value_representation,
            title=title,
            grain_fields=grain_fields,
            metric_id=metric_id,
            metric_definition=metric_definition,
            metric_version=metric_version,
            metric_basis_field=metric_basis_field,
            source_unit=source_unit,
            conversion_kind=conversion_kind,
            conversion_factor=conversion_factor,
            conversion_basis=conversion_basis,
            source_value_field=source_value_field,
            source_unit_basis_field=source_unit_basis_field,
            evidence_scope=evidence_scope,
            population=population,
            population_size=population_size,
            sample_size=sample_size,
            sampling_method=sampling_method,
            sample_member_field=sample_member_field,
            weight_field=weight_field,
            generalizes_to_population=generalizes_to_population,
            control_total=control_total,
            control_total_source=control_total_source,
            reconciliation_tolerance=reconciliation_tolerance,
            numerator=numerator,
            denominator=denominator,
            cohort=cohort,
            denominator_basis_field=denominator_basis_field,
            top_n=top_n,
            omitted_behavior=omitted_behavior,
            other_label=other_label,
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
        value_representation: str | None = None,
        title: str | None = None,
        grain_fields: tuple[str, ...] | list[str] | None = None,
        metric_id: str | None = None,
        metric_definition: str | None = None,
        metric_version: str | None = None,
        metric_basis_field: str | None = None,
        source_unit: str | None = None,
        conversion_kind: str | None = None,
        conversion_factor: float | int | None = None,
        conversion_basis: str | None = None,
        source_value_field: str | None = None,
        source_unit_basis_field: str | None = None,
        evidence_scope: str | None = None,
        population: str | None = None,
        population_size: int | None = None,
        sample_size: int | None = None,
        sampling_method: str | None = None,
        sample_member_field: str | None = None,
        weight_field: str | None = None,
        generalizes_to_population: bool | None = None,
        control_total: float | int | None = None,
        control_total_source: str | None = None,
        reconciliation_tolerance: float | int | None = None,
        interval_lower_field: str | None = None,
        interval_upper_field: str | None = None,
        interval_kind: str | None = None,
        interval_level: float | int | None = None,
        interval_method: str | None = None,
        metric_direction: str | None = None,
        numerator: str | None = None,
        denominator: str | None = None,
        cohort: str | None = None,
        denominator_basis_field: str | None = None,
        baseline_field: str | None = None,
        baseline_value: str | int | float | None = None,
        target_value: str | int | float | None = None,
        change_type: str | None = None,
        declared_change: float | int | None = None,
        window_kind: str | None = None,
        window_granularity: str | None = None,
        baseline_start: str | None = None,
        baseline_end: str | None = None,
        target_start: str | None = None,
        target_end: str | None = None,
        baseline_complete: bool | None = None,
        target_complete: bool | None = None,
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
            value_representation=value_representation,
            title=title,
            grain_fields=grain_fields,
            metric_id=metric_id,
            metric_definition=metric_definition,
            metric_version=metric_version,
            metric_basis_field=metric_basis_field,
            source_unit=source_unit,
            conversion_kind=conversion_kind,
            conversion_factor=conversion_factor,
            conversion_basis=conversion_basis,
            source_value_field=source_value_field,
            source_unit_basis_field=source_unit_basis_field,
            evidence_scope=evidence_scope,
            population=population,
            population_size=population_size,
            sample_size=sample_size,
            sampling_method=sampling_method,
            sample_member_field=sample_member_field,
            weight_field=weight_field,
            generalizes_to_population=generalizes_to_population,
            control_total=control_total,
            control_total_source=control_total_source,
            reconciliation_tolerance=reconciliation_tolerance,
            interval_lower_field=interval_lower_field,
            interval_upper_field=interval_upper_field,
            interval_kind=interval_kind,
            interval_level=interval_level,
            interval_method=interval_method,
            metric_direction=metric_direction,
            numerator=numerator,
            denominator=denominator,
            cohort=cohort,
            denominator_basis_field=denominator_basis_field,
            baseline_field=baseline_field,
            baseline_value=baseline_value,
            target_value=target_value,
            change_type=change_type,
            declared_change=declared_change,
            window_kind=window_kind,
            window_granularity=window_granularity,
            baseline_start=baseline_start,
            baseline_end=baseline_end,
            target_start=target_start,
            target_end=target_end,
            baseline_complete=baseline_complete,
            target_complete=target_complete,
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
        value_representation: str | None = None,
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
            value_representation=value_representation,
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
        value_representation: str | None = None,
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
            value_representation=value_representation,
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
        value_representation: str | None = None,
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
            value_representation=value_representation,
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
        value_representation: str | None = None,
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
            value_representation=value_representation,
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
        value_representation: str | None = None,
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
            value_representation=value_representation,
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
        value_representation: str | None = None,
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
            value_representation=value_representation,
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

    @classmethod
    def process_tree(
        cls,
        *,
        data: pd.DataFrame,
        node: str,
        parent: str,
        label: str,
        claim: str,
        branch: str | None = None,
        source: str | None = None,
        title: str | None = None,
        caveat: str | None = None,
        filters: Mapping[str, Any] | str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "Chart":
        """Build an audited rooted process/decision tree from one row per node."""

        return cls(
            intent="process_tree",
            data=data,
            node=node,
            parent=parent,
            label=label,
            branch=branch,
            claim=claim,
            source=source,
            title=title,
            caveat=caveat,
            filters=filters,
            metadata=metadata,
        )

    def audit(self) -> AuditReport:
        if self.intent == "process_tree":
            from .process_tree_audit import audit_process_tree_chart

            report = audit_process_tree_chart(self)
        elif self.intent == "set_membership":
            from .set_membership_audit import audit_set_membership_chart

            report = audit_set_membership_chart(self)
        elif self.intent in {"qq", "ecdf", "residual"}:
            from .statistical_audit import audit_statistical_chart

            report = audit_statistical_chart(self)
        else:
            report = audit_chart(self)

        from .input_binding import bind_chart_report

        return bind_chart_report(report, self)

    def to_altair(self) -> Any:
        from .renderers.altair import render_chart

        return render_chart(self)

    def to_vega_lite(self) -> dict[str, Any]:
        return self.to_altair().to_dict()
