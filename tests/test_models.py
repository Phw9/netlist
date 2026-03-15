"""Tests for Pydantic data models."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from netlist_converter.models import (
    Component,
    ComponentType,
    Net,
    Netlist,
    NetlistMetadata,
    Pin,
    PinRef,
)


class TestComponent:
    def test_create_resistor(self) -> None:
        comp = Component(
            reference="R1",
            component_type=ComponentType.RESISTOR,
            value="10k",
            pins=[
                Pin(number="1", name="A", pin_type="passive"),
                Pin(number="2", name="B", pin_type="passive"),
            ],
        )
        assert comp.reference == "R1"
        assert comp.pin_count == 2
        assert comp.component_type == ComponentType.RESISTOR

    def test_component_defaults(self) -> None:
        comp = Component(reference="X1", component_type=ComponentType.OTHER)
        assert comp.value == ""
        assert comp.pin_count == 0


class TestNet:
    def test_net_connection_count(self) -> None:
        net = Net(
            name="VCC",
            pins=[
                PinRef(component_ref="R1", pin="1"),
                PinRef(component_ref="U1", pin="VCC"),
            ],
        )
        assert net.connection_count == 2

    def test_empty_net(self) -> None:
        net = Net(name="EMPTY")
        assert net.connection_count == 0


class TestNetlist:
    def test_component_lookup(self, sample_netlist: Netlist) -> None:
        comp = sample_netlist.get_component("R1")
        assert comp is not None
        assert comp.value == "10k"

    def test_missing_component(self, sample_netlist: Netlist) -> None:
        assert sample_netlist.get_component("R999") is None

    def test_nets_for_component(self, sample_netlist: Netlist) -> None:
        nets = sample_netlist.get_nets_for_component("U1")
        assert len(nets) == 3
        net_names = {n.name for n in nets}
        assert "VCC" in net_names
        assert "GND" in net_names

    def test_json_round_trip(self, sample_netlist: Netlist) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.json"
            sample_netlist.save_json(path)
            loaded = Netlist.load_json(path)

        assert loaded.component_count == sample_netlist.component_count
        assert loaded.net_count == sample_netlist.net_count
        assert loaded.metadata.source_file == "test_circuit.png"

    def test_model_serialization(self, sample_netlist: Netlist) -> None:
        json_str = sample_netlist.model_dump_json()
        data = json.loads(json_str)
        restored = Netlist.model_validate(data)
        assert restored.component_count == 3
