"""Post-processing utilities for parsed component data."""

from __future__ import annotations

import re

from netlist_converter.models import Component, ComponentType

PREFIX_TO_TYPE: dict[str, ComponentType] = {
    "R": ComponentType.RESISTOR,
    "C": ComponentType.CAPACITOR,
    "L": ComponentType.INDUCTOR,
    "D": ComponentType.DIODE,
    "Q": ComponentType.TRANSISTOR,
    "U": ComponentType.IC,
    "J": ComponentType.CONNECTOR,
    "P": ComponentType.CONNECTOR,
    "LED": ComponentType.LED,
    "Y": ComponentType.CRYSTAL,
    "F": ComponentType.FUSE,
    "K": ComponentType.RELAY,
    "T": ComponentType.TRANSFORMER,
    "SW": ComponentType.SWITCH,
    "VR": ComponentType.VOLTAGE_REGULATOR,
}


def infer_component_type(reference: str) -> ComponentType:
    """Infer component type from its reference designator prefix."""
    ref_upper = reference.upper()
    for prefix, comp_type in sorted(PREFIX_TO_TYPE.items(), key=lambda x: -len(x[0])):
        if ref_upper.startswith(prefix):
            return comp_type
    return ComponentType.OTHER


def normalize_reference(reference: str) -> str:
    """Normalize a reference designator (strip whitespace, uppercase prefix)."""
    cleaned = reference.strip()
    match = re.match(r"([A-Za-z]+)(\d+)", cleaned)
    if match is None:
        return cleaned
    prefix = match.group(1).upper()
    number = match.group(2)
    return f"{prefix}{number}"


def validate_components(components: list[Component]) -> list[Component]:
    """Fix and deduplicate a list of components."""
    seen: dict[str, Component] = {}
    for comp in components:
        normalized_ref = normalize_reference(comp.reference)
        comp.reference = normalized_ref

        if comp.component_type == ComponentType.OTHER:
            comp.component_type = infer_component_type(normalized_ref)

        existing = seen.get(normalized_ref)
        if existing is None or len(comp.pins) > len(existing.pins):
            seen[normalized_ref] = comp

    return sorted(seen.values(), key=lambda c: c.reference)
