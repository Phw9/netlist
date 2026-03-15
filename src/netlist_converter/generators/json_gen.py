"""JSON/CSV netlist export generator."""

from __future__ import annotations

import csv
import io

from netlist_converter.generators.base import NetlistGenerator
from netlist_converter.models import Netlist


class JsonGenerator(NetlistGenerator):
    """Export netlist as pretty-printed JSON."""

    @property
    def file_extension(self) -> str:
        return ".json"

    def generate(self, netlist: Netlist) -> str:
        return netlist.model_dump_json(indent=2)


class CsvGenerator(NetlistGenerator):
    """Export netlist as two CSV sections: components and nets."""

    @property
    def file_extension(self) -> str:
        return ".csv"

    def generate(self, netlist: Netlist) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)

        writer.writerow(["# COMPONENTS"])
        writer.writerow([
            "Reference", "Type", "Value", "Footprint",
            "Manufacturer", "PartNumber", "Description",
        ])
        for comp in netlist.components:
            writer.writerow([
                comp.reference,
                comp.component_type.value,
                comp.value,
                comp.footprint,
                comp.manufacturer,
                comp.part_number,
                comp.description,
            ])

        writer.writerow([])
        writer.writerow(["# NETS"])
        writer.writerow(["NetName", "ComponentRef", "Pin"])
        for net in netlist.nets:
            for pin_ref in net.pins:
                writer.writerow([net.name, pin_ref.component_ref, pin_ref.pin])

        return buf.getvalue()
