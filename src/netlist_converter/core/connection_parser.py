"""Post-processing utilities for parsed net/connection data."""

from __future__ import annotations

from netlist_converter.models import Component, Net, PinRef

AUTO_NET_PREFIX = "NET"


def _generate_net_name(index: int) -> str:
    """Generate a sequential net name like NET001, NET002, etc."""
    return f"{AUTO_NET_PREFIX}{index:03d}"


def validate_nets(nets: list[Net], components: list[Component]) -> list[Net]:
    """Validate and clean net data against known components."""
    valid_refs = {c.reference for c in components}

    cleaned: list[Net] = []
    auto_index = 1

    for net in nets:
        valid_pins = [
            pin for pin in net.pins if pin.component_ref in valid_refs
        ]

        if len(valid_pins) < 2:
            continue

        name = net.name.strip()
        if not name:
            name = _generate_net_name(auto_index)
            auto_index += 1

        cleaned.append(Net(name=name, pins=valid_pins))

    return _deduplicate_nets(cleaned)


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

    result = [Net(name=name, pins=pins) for name, pins in sorted(by_name.items())]
    return result
