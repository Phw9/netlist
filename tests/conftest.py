"""Shared test fixtures."""

from __future__ import annotations

import pytest

from netlist_converter.models import (
    Component,
    ComponentType,
    Net,
    Netlist,
    NetlistMetadata,
    Pin,
    PinRef,
)


@pytest.fixture()
def sample_netlist() -> Netlist:
    """A minimal but realistic netlist for testing generators."""
    return Netlist(
        metadata=NetlistMetadata(
            source_file="test_circuit.png",
            llm_model="test-model",
            confidence=0.90,
        ),
        components=[
            Component(
                reference="R1",
                component_type=ComponentType.RESISTOR,
                value="10k",
                footprint="0805",
                pins=[
                    Pin(number="1", name="A", pin_type="passive"),
                    Pin(number="2", name="B", pin_type="passive"),
                ],
            ),
            Component(
                reference="C1",
                component_type=ComponentType.CAPACITOR,
                value="100nF",
                footprint="0402",
                pins=[
                    Pin(number="1", name="A", pin_type="passive"),
                    Pin(number="2", name="B", pin_type="passive"),
                ],
            ),
            Component(
                reference="U1",
                component_type=ComponentType.IC,
                value="LM7805",
                footprint="TO-220",
                pins=[
                    Pin(number="1", name="IN", pin_type="input"),
                    Pin(number="2", name="GND", pin_type="power"),
                    Pin(number="3", name="OUT", pin_type="output"),
                ],
            ),
        ],
        nets=[
            Net(
                name="VCC",
                pins=[
                    PinRef(component_ref="R1", pin="1"),
                    PinRef(component_ref="U1", pin="1"),
                ],
            ),
            Net(
                name="GND",
                pins=[
                    PinRef(component_ref="C1", pin="2"),
                    PinRef(component_ref="U1", pin="2"),
                ],
            ),
            Net(
                name="NET001",
                pins=[
                    PinRef(component_ref="R1", pin="2"),
                    PinRef(component_ref="C1", pin="1"),
                    PinRef(component_ref="U1", pin="3"),
                ],
            ),
        ],
    )
