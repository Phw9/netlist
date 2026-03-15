"""Tests for netlist format generators."""

from __future__ import annotations

import tempfile
from pathlib import Path

from netlist_converter.config import OutputFormat
from netlist_converter.generators import create_generator
from netlist_converter.generators.edif import EdifGenerator
from netlist_converter.generators.json_gen import CsvGenerator, JsonGenerator
from netlist_converter.generators.kicad import KicadGenerator
from netlist_converter.generators.spice import SpiceGenerator
from netlist_converter.models import Netlist


class TestSpiceGenerator:
    def test_generate_contains_components(self, sample_netlist: Netlist) -> None:
        gen = SpiceGenerator()
        output = gen.generate(sample_netlist)
        assert "R1" in output
        assert "C1" in output
        assert ".end" in output

    def test_file_extension(self) -> None:
        assert SpiceGenerator().file_extension == ".cir"

    def test_write_file(self, sample_netlist: Netlist) -> None:
        gen = SpiceGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = gen.write(sample_netlist, Path(tmpdir) / "output")
            assert path.suffix == ".cir"
            assert path.exists()
            content = path.read_text()
            assert ".end" in content


class TestEdifGenerator:
    def test_generate_valid_structure(self, sample_netlist: Netlist) -> None:
        gen = EdifGenerator()
        output = gen.generate(sample_netlist)
        assert "(edif " in output
        assert "(edifVersion 2 0 0)" in output
        assert "(cell R1" in output
        assert "(net VCC" in output

    def test_file_extension(self) -> None:
        assert EdifGenerator().file_extension == ".edf"


class TestKicadGenerator:
    def test_generate_valid_structure(self, sample_netlist: Netlist) -> None:
        gen = KicadGenerator()
        output = gen.generate(sample_netlist)
        assert "(export (version D)" in output
        assert '(ref R1)' in output
        assert '(name "VCC")' in output

    def test_file_extension(self) -> None:
        assert KicadGenerator().file_extension == ".net"


class TestJsonGenerator:
    def test_generate_valid_json(self, sample_netlist: Netlist) -> None:
        gen = JsonGenerator()
        output = gen.generate(sample_netlist)
        import json
        data = json.loads(output)
        assert len(data["components"]) == 3
        assert len(data["nets"]) == 3


class TestCsvGenerator:
    def test_generate_csv_content(self, sample_netlist: Netlist) -> None:
        gen = CsvGenerator()
        output = gen.generate(sample_netlist)
        assert "# COMPONENTS" in output
        assert "# NETS" in output
        assert "R1" in output
        assert "VCC" in output


class TestFactory:
    def test_create_spice(self) -> None:
        gen = create_generator(OutputFormat.SPICE)
        assert isinstance(gen, SpiceGenerator)

    def test_create_edif(self) -> None:
        gen = create_generator(OutputFormat.EDIF)
        assert isinstance(gen, EdifGenerator)

    def test_create_kicad(self) -> None:
        gen = create_generator(OutputFormat.KICAD)
        assert isinstance(gen, KicadGenerator)

    def test_create_json(self) -> None:
        gen = create_generator(OutputFormat.JSON)
        assert isinstance(gen, JsonGenerator)
