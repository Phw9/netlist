"""Post-processing utilities for parsed net/connection data."""

from __future__ import annotations

import logging
import re

from netlist_converter.models import Component, Net, PinRef

logger = logging.getLogger(__name__)

AUTO_NET_PREFIX = "NET"


def _generate_net_name(index: int) -> str:
    """Generate a sequential net name like NET001, NET002, etc."""
    return f"{AUTO_NET_PREFIX}{index:03d}"


def _normalize_ref(reference: str) -> str:
    """Apply the same normalization as component_parser to a component ref string."""
    cleaned = reference.strip()
    match = re.match(r"([A-Za-z]+)(\d+)", cleaned)
    if match is None:
        return cleaned
    return f"{match.group(1).upper()}{match.group(2)}"


def validate_nets(nets: list[Net], components: list[Component]) -> list[Net]:
    """Validate and clean net data against known components.

    Normalizes component_ref in each net pin so they match the normalized
    component references produced by validate_components.
    Logs when nets or pins are dropped.
    """
    valid_refs = {c.reference for c in components}
    logger.debug("Known component refs: %s", sorted(valid_refs))

    cleaned: list[Net] = []
    auto_index = 1

    for net in nets:
        valid_pins: list[PinRef] = []
        for pin in net.pins:
            normalized = _normalize_ref(pin.component_ref)
            if normalized in valid_refs:
                valid_pins.append(PinRef(component_ref=normalized, pin=pin.pin))
            else:
                logger.debug(
                    "Net '%s': dropping pin (%s:%s) — ref '%s' (normalized '%s') not in components",
                    net.name, pin.component_ref, pin.pin, pin.component_ref, normalized,
                )

        if len(valid_pins) < 2:
            logger.debug(
                "Dropping net '%s' — only %d valid pin(s) after filtering (need >= 2)",
                net.name, len(valid_pins),
            )
            continue

        name = net.name.strip()
        if not name:
            name = _generate_net_name(auto_index)
            auto_index += 1

        cleaned.append(Net(name=name, pins=valid_pins))

    result = _deduplicate_nets(cleaned)
    logger.info(
        "Net validation: %d raw nets → %d valid nets (from %d components)",
        len(nets), len(result), len(components),
    )
    return result


def _deduplicate_nets(nets: list[Net]) -> list[Net]:
    """Merge nets that share the same name."""
    by_name: dict[str, list[PinRef]] = {}
    for net in nets:
        existing = by_name.get(net.name, [])
        seen_keys = {(p.component_ref, p.pin) for p in existing}
        for pin in net.pins:
            key = (pin.component_ref, pin.pin)
            if key not in seen_keys:
                existing.append(pin)
                seen_keys.add(key)
        by_name[net.name] = existing

    return [Net(name=name, pins=pins) for name, pins in sorted(by_name.items())]
