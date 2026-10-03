"""Policy checks for user-visible Vega-Lite defaults."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from numbers import Real
from typing import Any

import pandas as pd

from .audit import FAIL, PASS, AuditReport, audit_spec as _base_audit_spec
from .contracts import resolve_spec_claim
from .input_binding import BoundAuditReport, bind_spec_report
from .transforms import (
    build_transform_lineage,
    collect_transform_inventory,
    parse_transform_declaration,
    parse_transform_lineage,
)

SCALE_OVERRIDE_KEYS = {"domain", "domainMin", "domainMax", "domainRaw"}
SCALE_REQUEST_FLAG = "user_requested_scale_override"
NORMALIZATION_REQUEST_FLAG = "user_requested_normalization"


def audit_spec(
    spec: Mapping[str, Any],
    data: pd.DataFrame | Sequence[Mapping[str, Any]] | None = None,
    claim: str | None = None,
) -> BoundAuditReport:
    """Audit a spec and bind the verdict to the exact audited inputs."""

    resolved_claim = resolve_spec_claim(spec, claim)
    report = _base_audit_spec(spec=spec, data=data, claim=claim)
    _audit_transform_contract(report, spec)
    _audit_transform_lineage(report, spec)
    _audit_visual_default_consent(report, spec)
    return bind_spec_report(report, spec=spec, data=data, claim=resolved_claim)


def _audit_transform_contract(report: AuditReport, spec: Mapping[str, Any]) -> None:
    inventory = collect_transform_inventory(spec)

    if inventory.occurrences:
        for occurrence in inventory.occurrences:
            report.add(
                "transform.inventory",
                PASS,
                f"Detected explicit Vega-Lite transform kind {occurrence.kind!r}.",
                field=occurrence.location,
            )
    else:
        report.add(
            "transform.inventory",
            PASS,
            "No explicit Vega-Lite analytical transforms were detected.",
        )

    for location in inventory.malformed_locations:
        report.add(
            "transform.inventory",
            FAIL,
            "Transform entry could not be classified as exactly one supported Vega-Lite transform.",
            suggestion="Use one supported transform operator per transform entry.",
            field=location,
        )

    try:
        declared = parse_transform_declaration(spec)
    except ValueError as exc:
        report.add(
            "transform.declaration",
            FAIL,
            str(exc),
            suggestion=(
                "Declare the exact detected transform kinds as "
                "spec['usermeta']['transform_contract']['declared']."
            ),
            field="usermeta.transform_contract",
        )
        return

    detected = inventory.kinds
    if declared is None:
        if detected:
            report.add(
                "transform.declaration",
                FAIL,
                "Spec contains explicit analytical transforms without a transform declaration: "
                + ", ".join(detected)
                + ".",
                suggestion=(
                    "Add spec['usermeta']['transform_contract']={'declared': [...]} "
                    "with the exact detected transform kinds."
                ),
                field="usermeta.transform_contract",
            )
        else:
            report.add(
                "transform.declaration",
                PASS,
                "No explicit analytical transforms require declaration.",
            )
        return

    if declared == detected and not inventory.malformed_locations:
        report.add(
            "transform.declaration",
            PASS,
            "Transform declaration exactly matches the detected transform kinds: "
            + (", ".join(detected) if detected else "none")
            + ".",
        )
        return

    declared_set = set(declared)
    detected_set = set(detected)
    missing = sorted(detected_set - declared_set)
    stale = sorted(declared_set - detected_set)
    details: list[str] = []
    if missing:
        details.append("undeclared detected kinds: " + ", ".join(missing))
    if stale:
        details.append("declared but not detected kinds: " + ", ".join(stale))
    if inventory.malformed_locations:
        details.append("unclassified transform entries are present")
    report.add(
        "transform.declaration",
        FAIL,
        "Transform declaration does not match the audited spec (" + "; ".join(details) + ").",
        suggestion="Update the declaration to exactly match the spec and rerun the audit.",
        field="usermeta.transform_contract.declared",
    )


def _audit_transform_lineage(report: AuditReport, spec: Mapping[str, Any]) -> None:
    expected = build_transform_lineage(spec)
    expected_receipts = expected["receipts"]

    try:
        declared = parse_transform_lineage(spec)
    except ValueError as exc:
        report.add(
            "transform.lineage.receipts",
            FAIL,
            str(exc),
            suggestion=(
                "Regenerate spec['usermeta']['transform_lineage'] with "
                "chart_contract.build_transform_lineage(spec)."
            ),
            field="usermeta.transform_lineage",
        )
        return

    if not expected_receipts:
        if declared is None or declared == expected:
            report.add(
                "transform.lineage.receipts",
                PASS,
                "No transform lineage receipts are required for this spec.",
            )
        else:
            report.add(
                "transform.lineage.receipts",
                FAIL,
                "Transform lineage metadata is stale: receipts are present but no auditable transforms remain.",
                suggestion="Remove stale lineage metadata or regenerate it from the current spec.",
                field="usermeta.transform_lineage",
            )
        return

    if declared is None:
        report.add(
            "transform.lineage.receipts",
            FAIL,
            f"Spec contains {len(expected_receipts)} auditable transform occurrence(s) without lineage receipts.",
            suggestion=(
                "Set spec['usermeta']['transform_lineage'] = "
                "chart_contract.build_transform_lineage(spec) after the transform structure is final."
            ),
            field="usermeta.transform_lineage",
        )
        return

    if declared == expected:
        derived_outputs = sorted(
            {
                field
                for receipt in expected_receipts
                for field in receipt["output_fields"]
            }
        )
        message = (
            f"Transform lineage receipts exactly match {len(expected_receipts)} "
            "audited transform occurrence(s)."
        )
        if derived_outputs:
            message += " Declared derived output field(s): " + ", ".join(derived_outputs) + "."
        report.add("transform.lineage.receipts", PASS, message)
        return

    expected_by_location = {receipt["location"]: receipt for receipt in expected_receipts}
    declared_by_location = {receipt["location"]: receipt for receipt in declared["receipts"]}
    missing = sorted(set(expected_by_location) - set(declared_by_location))
    stale = sorted(set(declared_by_location) - set(expected_by_location))
    changed = sorted(
        location
        for location in set(expected_by_location) & set(declared_by_location)
        if expected_by_location[location] != declared_by_location[location]
    )
    details: list[str] = []
    if missing:
        details.append("missing receipt(s): " + ", ".join(missing))
    if stale:
        details.append("stale receipt(s): " + ", ".join(stale))
    if changed:
        details.append("changed receipt(s): " + ", ".join(changed))
    report.add(
        "transform.lineage.receipts",
        FAIL,
        "Transform lineage does not match the current spec (" + "; ".join(details) + ").",
        suggestion="Regenerate lineage receipts from the final transform structure.",
        field="usermeta.transform_lineage.receipts",
    )


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
