"""EDIF 2.0.0 netlist (.edf) generator for Zuken CR-5000/CR-8000 compatibility."""

from __future__ import annotations

from netlist_converter.generators.base import NetlistGenerator
from netlist_converter.models import Component, Net, Netlist

INDENT = "  "


def _edif_name(name: str) -> str:
    """Sanitize a name for EDIF (alphanumeric and underscore only)."""
    sanitized = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
    if sanitized and sanitized[0].isdigit():
        sanitized = f"N{sanitized}"
    return sanitized


def _build_cell(comp: Component, depth: int) -> list[str]:
    """Build EDIF cell definition for a single component."""
    prefix = INDENT * depth
    lines: list[str] = []
    cell_name = _edif_name(comp.reference)

    lines.append(f'{prefix}(cell {cell_name} (cellType GENERIC)')
    lines.append(f"{prefix}{INDENT}(view netlist (viewType NETLIST)")
    lines.append(f"{prefix}{INDENT}{INDENT}(interface")

    for pin in comp.pins:
        pin_name = _edif_name(pin.number)
        direction = "INPUT" if pin.pin_type == "input" else (
            "OUTPUT" if pin.pin_type == "output" else "INOUT"
        )
        lines.append(
            f"{prefix}{INDENT}{INDENT}{INDENT}(port {pin_name} (direction {direction}))"
        )

    lines.append(f"{prefix}{INDENT}{INDENT})")
    lines.append(f"{prefix}{INDENT}))")
    return lines


def _build_instance(comp: Component, depth: int) -> list[str]:
    """Build EDIF instance reference."""
    prefix = INDENT * depth
    cell_name = _edif_name(comp.reference)
    lines: list[str] = [
        f"{prefix}(instance {cell_name}",
        f"{prefix}{INDENT}(viewRef netlist (cellRef {cell_name}))",
    ]
    if comp.value:
        lines.append(
            f'{prefix}{INDENT}(property VALUE (string "{comp.value}"))'
        )
    lines.append(f"{prefix})")
    return lines


def _build_net(net: Net, depth: int) -> list[str]:
    """Build EDIF net definition."""
    prefix = INDENT * depth
    net_name = _edif_name(net.name)
    lines: list[str] = [f"{prefix}(net {net_name} (joined"]
    for pin_ref in net.pins:
        comp_name = _edif_name(pin_ref.component_ref)
        pin_name = _edif_name(pin_ref.pin)
        lines.append(f"{prefix}{INDENT}(portRef {pin_name} (instanceRef {comp_name}))")
    lines.append(f"{prefix}))")
    return lines


class EdifGenerator(NetlistGenerator):
    """Generate EDIF 2.0.0 netlist files compatible with Zuken import."""

    @property
    def file_extension(self) -> str:
        return ".edf"

    def generate(self, netlist: Netlist) -> str:
        lines: list[str] = []

        lines.append('(edif netlist_converter_output')
        lines.append(f'{INDENT}(edifVersion 2 0 0)')
        lines.append(f'{INDENT}(edifLevel 0)')
        lines.append(f'{INDENT}(keywordMap (keywordLevel 0))')
        lines.append(f'{INDENT}(status')
        lines.append(f'{INDENT}{INDENT}(written')
        lines.append(f'{INDENT}{INDENT}{INDENT}(timeStamp 0 0 0 0 0 0)')
        lines.append(
            f'{INDENT}{INDENT}{INDENT}(program "netlist-converter" '
            f'(version "{netlist.metadata.tool_version}"))'
        )
        lines.append(f'{INDENT}{INDENT})')
        lines.append(f'{INDENT})')

        lines.append(f'{INDENT}(library components (edifLevel 0) '
                      f'(technology (numberDefinition))')

        for comp in netlist.components:
            lines.extend(_build_cell(comp, depth=2))

        lines.append(f'{INDENT})')

        lines.append(f'{INDENT}(design root (cellRef root)')
        lines.append(f'{INDENT}{INDENT}(contents')

        for comp in netlist.components:
            lines.extend(_build_instance(comp, depth=3))

        for net in netlist.nets:
            lines.extend(_build_net(net, depth=3))

        lines.append(f'{INDENT}{INDENT})')
        lines.append(f'{INDENT})')
        lines.append(')')
        lines.append('')

        return "\n".join(lines)
