"""PCB component data models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ComponentType(str, Enum):
    """Standard PCB component categories."""

    RESISTOR = "resistor"
    CAPACITOR = "capacitor"
    INDUCTOR = "inductor"
    DIODE = "diode"
    TRANSISTOR = "transistor"
    IC = "ic"
    CONNECTOR = "connector"
    LED = "led"
    CRYSTAL = "crystal"
    FUSE = "fuse"
    RELAY = "relay"
    TRANSFORMER = "transformer"
    SWITCH = "switch"
    VOLTAGE_REGULATOR = "voltage_regulator"
    OPAMP = "opamp"
    OTHER = "other"


class Pin(BaseModel):
    """A single pin on a component."""

    number: str = Field(description="Pin number or name (e.g. '1', 'VCC', 'A1')")
    name: str = Field(default="", description="Functional pin name (e.g. 'IN', 'OUT', 'GND')")
    pin_type: str = Field(default="passive", description="Pin type: input, output, passive, power")


class Component(BaseModel):
    """A single PCB component with its properties."""

    reference: str = Field(description="Reference designator (e.g. R1, C3, U2)")
    component_type: ComponentType = Field(description="Component category")
    value: str = Field(default="", description="Component value (e.g. '10k', '100nF', 'LM7805')")
    footprint: str = Field(default="", description="Package footprint (e.g. '0805', 'SOT-23')")
    manufacturer: str = Field(default="", description="Manufacturer name")
    part_number: str = Field(default="", description="Manufacturer part number")
    description: str = Field(default="", description="Brief functional description")
    pins: list[Pin] = Field(default_factory=list, description="List of component pins")

    @property
    def pin_count(self) -> int:
        return len(self.pins)
