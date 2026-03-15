"""Netlist format generators and factory."""

from __future__ import annotations

from netlist_converter.config import OutputFormat
from netlist_converter.generators.base import NetlistGenerator
from netlist_converter.generators.edif import EdifGenerator
from netlist_converter.generators.json_gen import CsvGenerator, JsonGenerator
from netlist_converter.generators.kicad import KicadGenerator
from netlist_converter.generators.spice import SpiceGenerator

_GENERATORS: dict[OutputFormat, type[NetlistGenerator]] = {
    OutputFormat.SPICE: SpiceGenerator,
    OutputFormat.EDIF: EdifGenerator,
    OutputFormat.KICAD: KicadGenerator,
    OutputFormat.JSON: JsonGenerator,
}


def create_generator(fmt: OutputFormat) -> NetlistGenerator:
    """Factory: return the appropriate generator for the requested format."""
    gen_cls = _GENERATORS.get(fmt, SpiceGenerator)
    return gen_cls()


def create_csv_generator() -> CsvGenerator:
    """Return a CSV generator (always available as supplementary export)."""
    return CsvGenerator()


__all__ = [
    "CsvGenerator",
    "EdifGenerator",
    "JsonGenerator",
    "KicadGenerator",
    "NetlistGenerator",
    "SpiceGenerator",
    "create_csv_generator",
    "create_generator",
]
