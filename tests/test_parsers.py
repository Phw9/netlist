"""Tests for component_parser and connection_parser modules."""

from __future__ import annotations

from netlist_converter.core.component_parser import (
    infer_component_type,
    normalize_reference,
    validate_components,
)
from netlist_converter.core.connection_parser import validate_nets
from netlist_converter.models import Component, ComponentType, Net, Pin, PinRef


class TestInferComponentType:
    def test_resistor(self) -> None:
        assert infer_component_type("R1") == ComponentType.RESISTOR

    def test_capacitor(self) -> None:
        assert infer_component_type("C10") == ComponentType.CAPACITOR

    def test_ic(self) -> None:
        assert infer_component_type("U3") == ComponentType.IC

    def test_led(self) -> None:
        assert infer_component_type("LED1") == ComponentType.LED

    def test_switch(self) -> None:
        assert infer_component_type("SW2") == ComponentType.SWITCH

    def test_unknown(self) -> None:
        assert infer_component_type("Z99") == ComponentType.OTHER


class TestNormalizeReference:
    def test_basic(self) -> None:
        assert normalize_reference("r1") == "R1"
        assert normalize_reference("  C10  ") == "C10"

    def test_non_standard(self) -> None:
        assert normalize_reference("abc") == "abc"


class TestValidateComponents:
    def test_dedup_and_sort(self) -> None:
        components = [
            Component(reference="R2", component_type=ComponentType.RESISTOR, value="1k"),
            Component(reference="R1", component_type=ComponentType.RESISTOR, value="10k"),
            Component(reference="r1", component_type=ComponentType.RESISTOR, value="10k",
                      pins=[Pin(number="1", name="A")]),
        ]
        result = validate_components(components)
        assert len(result) == 2
        assert result[0].reference == "R1"
        assert result[0].pin_count == 1
        assert result[1].reference == "R2"

    def test_infer_type(self) -> None:
        comp = Component(reference="C5", component_type=ComponentType.OTHER, value="100nF")
        result = validate_components([comp])
        assert result[0].component_type == ComponentType.CAPACITOR


class TestValidateNets:
    def test_remove_invalid_refs(self) -> None:
        components = [
            Component(reference="R1", component_type=ComponentType.RESISTOR),
            Component(reference="C1", component_type=ComponentType.CAPACITOR),
        ]
        nets = [
            Net(name="VCC", pins=[
                PinRef(component_ref="R1", pin="1"),
                PinRef(component_ref="MISSING", pin="1"),
                PinRef(component_ref="C1", pin="1"),
            ]),
            Net(name="ORPHAN", pins=[
                PinRef(component_ref="MISSING", pin="1"),
            ]),
        ]
        result = validate_nets(nets, components)
        assert len(result) == 1
        assert result[0].name == "VCC"
        assert result[0].connection_count == 2

    def test_auto_name_empty_nets(self) -> None:
        components = [
            Component(reference="R1", component_type=ComponentType.RESISTOR),
            Component(reference="R2", component_type=ComponentType.RESISTOR),
        ]
        nets = [
            Net(name="", pins=[
                PinRef(component_ref="R1", pin="1"),
                PinRef(component_ref="R2", pin="1"),
            ]),
        ]
        result = validate_nets(nets, components)
        assert result[0].name == "NET001"
