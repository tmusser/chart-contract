"""Explicit control-total reconciliation for additive component decompositions."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from .contracts import is_ratio_like_unit

RECONCILIATION_CONTRACT_KEY = "reconciliation_contract"
RECONCILIATION_CONTRACT_VERSION = 1
RECONCILIATION_INTENTS = {"rank", "compare"}
RECONCILIATION_KIND = "sum"


@dataclass(frozen=True, slots=True)
class ReconciliationSummary:
    component_field: str
    metric_field: str
    reconciliation: str
    control_total: float
    control_total_source: str | None
    tolerance: float
    component_count: int
    component_total: float
    residual: float
    represented_share: float | None

    def to_dict(self) -> dict[str, Any]:
        return {"version": RECONCILIATION_CONTRACT_VERSION, **asdict(self)}


def chart_reconciliation_declaration(chart: Any) -> dict[str, Any] | None:
    values = (
        getattr(chart, "control_total", None),
        getattr(chart, "control_total_source", None),
        getattr(chart, "reconciliation_tolerance", None),
    )
    if all(value is None for value in values):
        return None
    return {
        "component_field": getattr(chart, "x", None),
        "metric_field": getattr(chart, "y", None),
        "control_total": getattr(chart, "control_total", None),
        "control_total_source": getattr(chart, "control_total_source", None),
        "tolerance": (
            0.0
            if getattr(chart, "reconciliation_tolerance", None) is None
            else getattr(chart, "reconciliation_tolerance")
        ),
        "unit": getattr(chart, "unit", None),
    }


def build_reconciliation_summary(
    frame: pd.DataFrame,
    *,
    component_field: Any,
    metric_field: Any,
    control_total: Any,
    control_total_source: Any = None,
    tolerance: Any = 0.0,
    unit: str | None = None,
) -> ReconciliationSummary:
    component = _required_string(component_field, "component_field")
    metric = _required_string(metric_field, "metric_field")
    total = _finite_number(control_total, "control_total")
    tol = _nonnegative_finite_number(tolerance, "tolerance")
    source = _optional_string(control_total_source, "control_total_source")

    if is_ratio_like_unit(unit):
        raise ValueError(
            "Control-total sum reconciliation is not supported for percent/rate/ratio metrics."
        )
    if component == metric:
        raise ValueError("Reconciliation component_field and metric_field must be distinct.")
    missing = [field for field in (component, metric) if field not in frame.columns]
    if missing:
        raise ValueError(
            "Reconciliation evidence is missing field(s): " + ", ".join(missing) + "."
        )

    components = frame[component]
    if components.isna().any():
        raise ValueError(f"Reconciliation component field '{component}' contains null values.")
    for raw in components.tolist():
        if isinstance(raw, str) and not raw.strip():
            raise ValueError(
                f"Reconciliation component field '{component}' contains blank labels."
            )
    duplicated = components.duplicated(keep=False)
    if duplicated.any():
        duplicate_count = int(duplicated.sum())
        raise ValueError(
            f"Reconciliation component field '{component}' must identify one row per component; "
            f"{duplicate_count} rows participate in duplicate component labels."
        )

    values: list[float] = []
    for raw in frame[metric].tolist():
        if pd.isna(raw):
            raise ValueError(f"Reconciliation metric field '{metric}' contains null values.")
        if isinstance(raw, bool):
            raise ValueError(
                f"Reconciliation metric field '{metric}' must be numeric, not boolean."
            )
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Reconciliation metric field '{metric}' must contain numeric values."
            ) from exc
        if not math.isfinite(value):
            raise ValueError(
                f"Reconciliation metric field '{metric}' must contain finite values."
            )
        values.append(value)

    if not values:
        raise ValueError("Reconciliation contract has no supplied component observations.")

    component_total = float(sum(values))
    residual = float(total - component_total)
    represented_share = (
        component_total / total
        if total > 0 and all(value >= 0 for value in values)
        else None
    )

    return ReconciliationSummary(
        component_field=component,
        metric_field=metric,
        reconciliation=RECONCILIATION_KIND,
        control_total=total,
        control_total_source=source,
        tolerance=tol,
        component_count=len(values),
        component_total=component_total,
        residual=residual,
        represented_share=represented_share,
    )


def reconciliation_matches(summary: ReconciliationSummary) -> bool:
    return math.isclose(
        summary.component_total,
        summary.control_total,
        rel_tol=1e-9,
        abs_tol=summary.tolerance,
    )


def parse_reconciliation_contract(spec: Mapping[str, Any]) -> dict[str, Any] | None:
    usermeta = spec.get("usermeta")
    if not isinstance(usermeta, Mapping) or RECONCILIATION_CONTRACT_KEY not in usermeta:
        return None

    contract = usermeta.get(RECONCILIATION_CONTRACT_KEY)
    if not isinstance(contract, Mapping):
        raise ValueError("usermeta.reconciliation_contract must be an object.")

    expected = {
        "version",
        "component_field",
        "metric_field",
        "reconciliation",
        "control_total",
        "control_total_source",
        "tolerance",
        "component_count",
        "component_total",
        "residual",
        "represented_share",
    }
    if set(contract) != expected:
        missing = sorted(expected - set(contract))
        extra = sorted(set(contract) - expected)
        details: list[str] = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("unsupported: " + ", ".join(extra))
        raise ValueError(
            "usermeta.reconciliation_contract must use the exact v1 field set"
            + (" (" + "; ".join(details) + ")" if details else "")
            + "."
        )
    if contract.get("version") != RECONCILIATION_CONTRACT_VERSION:
        raise ValueError(
            "usermeta.reconciliation_contract.version must equal "
            f"{RECONCILIATION_CONTRACT_VERSION}."
        )

    component_field = _required_string(contract.get("component_field"), "component_field")
    metric_field = _required_string(contract.get("metric_field"), "metric_field")
    if component_field == metric_field:
        raise ValueError(
            "usermeta.reconciliation_contract component_field and metric_field must be distinct."
        )
    if contract.get("reconciliation") != RECONCILIATION_KIND:
        raise ValueError(
            "usermeta.reconciliation_contract.reconciliation must equal 'sum'."
        )

    control_total = _finite_number(contract.get("control_total"), "control_total")
    control_total_source = _optional_string(
        contract.get("control_total_source"),
        "control_total_source",
    )
    tolerance = _nonnegative_finite_number(contract.get("tolerance"), "tolerance")

    component_count = contract.get("component_count")
    if isinstance(component_count, bool) or not isinstance(component_count, int) or component_count <= 0:
        raise ValueError(
            "usermeta.reconciliation_contract.component_count must be a positive integer."
        )

    component_total = _finite_number(contract.get("component_total"), "component_total")
    residual = _finite_number(contract.get("residual"), "residual")
    if not math.isclose(
        component_total + residual,
        control_total,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        raise ValueError(
            "Reconciliation component_total + residual must equal control_total."
        )

    represented_share = contract.get("represented_share")
    if represented_share is not None:
        represented_share = _finite_number(represented_share, "represented_share")
        if control_total <= 0:
            raise ValueError(
                "Reconciliation represented_share must be null when control_total <= 0."
            )
        expected_share = component_total / control_total
        if not math.isclose(
            represented_share,
            expected_share,
            rel_tol=1e-9,
            abs_tol=1e-9,
        ):
            raise ValueError(
                "Reconciliation represented_share must equal component_total / control_total."
            )

    return {
        "version": RECONCILIATION_CONTRACT_VERSION,
        "component_field": component_field,
        "metric_field": metric_field,
        "reconciliation": RECONCILIATION_KIND,
        "control_total": control_total,
        "control_total_source": control_total_source,
        "tolerance": tolerance,
        "component_count": component_count,
        "component_total": component_total,
        "residual": residual,
        "represented_share": represented_share,
    }


def summaries_match(
    declared: Mapping[str, Any],
    actual: ReconciliationSummary,
) -> bool:
    if declared["component_field"] != actual.component_field:
        return False
    if declared["metric_field"] != actual.metric_field:
        return False
    if declared["reconciliation"] != actual.reconciliation:
        return False
    if declared["control_total_source"] != actual.control_total_source:
        return False
    if declared["component_count"] != actual.component_count:
        return False
    for name in ("control_total", "tolerance", "component_total", "residual"):
        if not math.isclose(
            float(declared[name]),
            float(getattr(actual, name)),
            rel_tol=1e-9,
            abs_tol=1e-9,
        ):
            return False
    declared_share = declared["represented_share"]
    actual_share = actual.represented_share
    if (declared_share is None) != (actual_share is None):
        return False
    if declared_share is not None and not math.isclose(
        float(declared_share),
        float(actual_share),
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        return False
    return True


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"usermeta.reconciliation_contract.{field} must be a non-empty string."
        )
    return value.strip()


def _optional_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"usermeta.reconciliation_contract.{field} must be null or a non-empty string."
        )
    return value.strip()


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"usermeta.reconciliation_contract.{field} must be a finite number."
        )
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(
            f"usermeta.reconciliation_contract.{field} must be a finite number."
        )
    return number


def _nonnegative_finite_number(value: Any, field: str) -> float:
    number = _finite_number(value, field)
    if number < 0:
        raise ValueError(
            f"usermeta.reconciliation_contract.{field} must be non-negative."
        )
    return number
