"""Policy checks for user-visible Vega-Lite defaults."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from numbers import Real
from typing import Any

import pandas as pd

from .audit import FAIL, PASS, AuditReport, audit_spec as _base_audit_spec

SCALE_OVERRIDE_KEYS = {"domain", "domainMin", "domainMax", "domainRaw"}
SCALE_REQUEST_FLAG = "user_requested_scale_override"
NORMALIZATION_REQUEST_FLAG = "user_requested_normalization"


def audit_spec(
    spec: Mapping[str, Any],
    data: pd.DataFrame | Sequence[Mapping[str, Any]] | None = None,
    claim: str | None = None,
) -> AuditReport:
    """Audit a spec, including explicit-consent checks for visual transformations."""

    report = _base_audit_spec(spec=spec, data=data, claim=claim)
    _audit_visual_default_consent(report, spec)
    return report


def _audit_visual_default_consent(report: AuditReport, spec: Mapping[str, Any]) -> None:
    views = list(_iter_views(spec))
    scale_override = any(_view_has_quantitative_scale_override(view) for view in views)
    normalization = any(_view_uses_normalization(view) for view in views)
    truncated_bar_domain = any(_view_has_bar_domain_excluding_zero(view) for view in views)

    if scale_override:
        if _user_requested(spec, SCALE_REQUEST_FLAG):
            report.add(
                "scale.override.authorization",
                PASS,
                "Quantitative scale override is explicitly declared as user-requested.",
            )
        else:
            report.add(
                "scale.override.authorization",
                FAIL,
                "Spec changes a quantitative scale without an explicit user-request declaration.",
                suggestion=(
                    f"Remove the scale override, or set spec['usermeta']['{SCALE_REQUEST_FLAG}']=true "
                    "only when the user explicitly requested the changed scale."
                ),
                field="usermeta.user_requested_scale_override",
            )
    else:
        report.add(
            "scale.override.authorization",
            PASS,
            "No explicit quantitative scale override was detected.",
        )

    if normalization:
        if _user_requested(spec, NORMALIZATION_REQUEST_FLAG):
            report.add(
                "scale.normalization.authorization",
                PASS,
                "Normalization is explicitly declared as user-requested.",
            )
        else:
            report.add(
                "scale.normalization.authorization",
                FAIL,
                "Spec normalizes values without an explicit user-request declaration.",
                suggestion=(
                    f"Remove normalization, or set spec['usermeta']['{NORMALIZATION_REQUEST_FLAG}']=true "
                    "only when the user explicitly requested normalized values."
                ),
                field="usermeta.user_requested_normalization",
            )
    else:
        report.add(
            "scale.normalization.authorization",
            PASS,
            "No native Vega-Lite normalization was detected.",
        )

    if truncated_bar_domain:
        report.add(
            "scale.bar.explicit_domain_zero",
            FAIL,
            "Bar chart uses an explicit quantitative domain that excludes zero.",
            suggestion="Include zero in the quantitative bar domain or remove the explicit domain override.",
            field="encoding.*.scale",
        )


def _user_requested(spec: Mapping[str, Any], flag: str) -> bool:
    usermeta = spec.get("usermeta")
    return isinstance(usermeta, Mapping) and usermeta.get(flag) is True


def _iter_views(spec: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    yield spec

    for collection_key in ("layer", "concat", "hconcat", "vconcat"):
        nested = spec.get(collection_key)
        if not isinstance(nested, list):
            continue
        for item in nested:
            if isinstance(item, Mapping):
                yield from _iter_views(item)

    nested_spec = spec.get("spec")
    if isinstance(nested_spec, Mapping):
        yield from _iter_views(nested_spec)


def _view_has_quantitative_scale_override(view: Mapping[str, Any]) -> bool:
    encoding = view.get("encoding")
    if not isinstance(encoding, Mapping):
        return False

    for channel in ("x", "y"):
        definition = encoding.get(channel)
        if not isinstance(definition, Mapping) or not _is_quantitative(definition):
            continue
        scale = definition.get("scale")
        if not isinstance(scale, Mapping):
            continue
        if scale.get("zero") is False:
            return True
        if any(key in scale for key in SCALE_OVERRIDE_KEYS):
            return True
    return False


def _view_has_bar_domain_excluding_zero(view: Mapping[str, Any]) -> bool:
    if _mark_type(view) != "bar":
        return False

    encoding = view.get("encoding")
    if not isinstance(encoding, Mapping):
        return False

    for channel in ("x", "y"):
        definition = encoding.get(channel)
        if not isinstance(definition, Mapping) or not _is_quantitative(definition):
            continue
        scale = definition.get("scale")
        if not isinstance(scale, Mapping) or scale.get("zero") is False:
            continue

        domain = scale.get("domain")
        if isinstance(domain, list) and domain and all(_is_real_number(value) for value in domain):
            numeric_domain = [float(value) for value in domain]
            if not (min(numeric_domain) <= 0 <= max(numeric_domain)):
                return True

        domain_min = scale.get("domainMin")
        if _is_real_number(domain_min) and float(domain_min) > 0:
            return True

        domain_max = scale.get("domainMax")
        if _is_real_number(domain_max) and float(domain_max) < 0:
            return True

    return False


def _view_uses_normalization(view: Mapping[str, Any]) -> bool:
    encoding = view.get("encoding")
    if isinstance(encoding, Mapping):
        for definition in encoding.values():
            if isinstance(definition, Mapping) and definition.get("stack") == "normalize":
                return True

    transforms = view.get("transform")
    if isinstance(transforms, list):
        for transform in transforms:
            if not isinstance(transform, Mapping):
                continue
            if "stack" in transform and transform.get("offset") == "normalize":
                return True
    return False


def _mark_type(view: Mapping[str, Any]) -> str:
    mark = view.get("mark")
    if isinstance(mark, str):
        return mark
    if isinstance(mark, Mapping):
        return str(mark.get("type", ""))
    return ""


def _is_quantitative(definition: Mapping[str, Any]) -> bool:
    return definition.get("type") in {"quantitative", "Q"}


def _is_real_number(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool)
