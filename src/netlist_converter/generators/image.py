"""Schematic image generator: render a Netlist as a block-diagram-style SVG/PNG."""

from __future__ import annotations

from pathlib import Path

import schemdraw
import schemdraw.elements as elm

from netlist_converter.models import ComponentType, Netlist

COMPONENT_DRAW_MAP: dict[ComponentType, type] = {
    ComponentType.RESISTOR: elm.Resistor,
    ComponentType.CAPACITOR: elm.Capacitor,
    ComponentType.INDUCTOR: elm.Inductor2,
    ComponentType.DIODE: elm.Diode,
    ComponentType.LED: elm.LED,
    ComponentType.OPAMP: elm.Opamp,
    ComponentType.FUSE: elm.Fuse,
    ComponentType.SWITCH: elm.Switch,
}

BLOCK_SPACING_X = 5.0
BLOCK_SPACING_Y = 3.0
COLUMNS_PER_ROW = 4


def _build_net_map(netlist: Netlist) -> dict[str, list[str]]:
    """Build a mapping of component_ref -> list of connected net names."""
    net_map: dict[str, list[str]] = {}
    for net in netlist.nets:
        for pin_ref in net.pins:
            comp_nets = net_map.setdefault(pin_ref.component_ref, [])
            if net.name not in comp_nets:
                comp_nets.append(net.name)
    return net_map


def _add_components_to_drawing(
    drawing: schemdraw.Drawing,
    netlist: Netlist,
    net_map: dict[str, list[str]],
    include_net_labels: bool = True,
) -> None:
    """Add all components as schemdraw elements to the drawing."""
    x_pos = 0.0
    y_pos = 0.0
    col = 0

    for comp in netlist.components:
        element_cls = COMPONENT_DRAW_MAP.get(comp.component_type)
        comp_label = f"{comp.reference}\n{comp.value}" if comp.value else comp.reference

        if element_cls is not None and element_cls != elm.Opamp:
            elem_instance = element_cls().at((x_pos, y_pos)).label(comp_label, loc="top")
        else:
            elem_instance = (
                elm.RBox(w=3, h=1.5).at((x_pos, y_pos)).label(comp_label, loc="center")
            )

        if include_net_labels:
            connected_nets = net_map.get(comp.reference, [])
            net_label = ", ".join(connected_nets[:3])
            elem_instance = elem_instance.label(net_label, loc="bottom", fontsize=8)

        drawing.add(elem_instance)

        col += 1
        if col >= COLUMNS_PER_ROW:
            col = 0
            x_pos = 0.0
            y_pos -= BLOCK_SPACING_Y
        else:
            x_pos += BLOCK_SPACING_X


def render_netlist_image(netlist: Netlist, output_path: Path) -> Path:
    """Render a netlist as a schematic block diagram SVG image."""
    final_path = output_path.with_suffix(".svg")

    with schemdraw.Drawing(show=False, file=str(final_path)) as d:
        d.config(fontsize=12)

        if not netlist.components:
            d.add(elm.Label().label("Empty Netlist").at((0, 0)))
            return final_path

        net_map = _build_net_map(netlist)
        _add_components_to_drawing(d, netlist, net_map)

    return final_path


def render_netlist_png(netlist: Netlist, output_path: Path) -> Path:
    """Render netlist as PNG image."""
    png_path = output_path.with_suffix(".png")

    with schemdraw.Drawing(show=False) as d:
        d.config(fontsize=12)

        if netlist.components:
            net_map = _build_net_map(netlist)
            _add_components_to_drawing(d, netlist, net_map, include_net_labels=False)

        img_bytes = d.get_imagedata("png")

    png_path.parent.mkdir(parents=True, exist_ok=True)
    png_path.write_bytes(img_bytes)
    return png_path
