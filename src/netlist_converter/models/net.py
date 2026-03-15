"""Net and connection data models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PinRef(BaseModel):
    """Reference to a specific pin on a component."""

    component_ref: str = Field(description="Component reference designator (e.g. 'R1', 'U2')")
    pin: str = Field(description="Pin number or name on the component")


class Net(BaseModel):
    """A named electrical net connecting multiple component pins."""

    name: str = Field(description="Net name (e.g. 'VCC', 'GND', 'NET001')")
    pins: list[PinRef] = Field(default_factory=list, description="Pins connected to this net")

    @property
    def connection_count(self) -> int:
        return len(self.pins)
