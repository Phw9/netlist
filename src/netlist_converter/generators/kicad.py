"""KiCad netlist (.net) generator using S-expression format."""

from __future__ import annotations

from datetime import datetime, timezone

from netlist_converter.generators.base import NetlistGenerator
from netlist_converter.models import Netlist

INDENT = "  "


class KicadGenerator(NetlistGenerator):
    """Generate KiCad-compatible .net netlist files."""

    @property
    def file_extension(self) -> str:
        return ".net"

    def generate(self, netlist: Netlist) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        lines: list[str] = []

        lines.append("(export (version D)")
        lines.append(f'{INDENT}(design')
        lines.append(f'{INDENT}{INDENT}(source "{netlist.metadata.source_file}")')
        lines.append(f'{INDENT}{INDENT}(date "{now}")')
        lines.append(f'{INDENT}{INDENT}(tool "netlist-converter {netlist.metadata.tool_version}")')
        lines.append(f'{INDENT})')

        lines.append(f'{INDENT}(components')
        for comp in netlist.components:
            lines.append(f'{INDENT}{INDENT}(comp (ref {comp.reference})')
            lines.append(f'{INDENT}{INDENT}{INDENT}(value "{comp.value}")')
            if comp.footprint:
                lines.append(f'{INDENT}{INDENT}{INDENT}(footprint "{comp.footprint}")')
            if comp.description:
                lines.append(
                    f'{INDENT}{INDENT}{INDENT}(datasheet "{comp.description}")'
                )
            lines.append(f'{INDENT}{INDENT})')
        lines.append(f'{INDENT})')

        lines.append(f'{INDENT}(nets')
        for idx, net in enumerate(netlist.nets, start=1):
            lines.append(f'{INDENT}{INDENT}(net (code {idx}) (name "{net.name}")')
            for pin_ref in net.pins:
                lines.append(
                    f'{INDENT}{INDENT}{INDENT}(node (ref {pin_ref.component_ref}) '
                    f'(pin {pin_ref.pin}))'
                )
            lines.append(f'{INDENT}{INDENT})')
        lines.append(f'{INDENT})')

        lines.append(")")
        lines.append("")

        return "\n".join(lines)
