"""Top-level netlist data model combining components and nets."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from netlist_converter.models.component import Component
from netlist_converter.models.net import Net


class NetlistMetadata(BaseModel):
    """Metadata about the netlist extraction."""

    source_file: str = Field(default="", description="Original input file name")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    tool_version: str = Field(default="0.1.0")
    llm_model: str = Field(default="", description="LLM model used for extraction")
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Overall extraction confidence"
    )


class Netlist(BaseModel):
    """Complete netlist containing components and their connections."""

    metadata: NetlistMetadata = Field(default_factory=NetlistMetadata)
    components: list[Component] = Field(default_factory=list)
    nets: list[Net] = Field(default_factory=list)

    @property
    def component_count(self) -> int:
        return len(self.components)

    @property
    def net_count(self) -> int:
        return len(self.nets)

    def get_component(self, reference: str) -> Component | None:
        """Find a component by its reference designator."""
        matches = [c for c in self.components if c.reference == reference]
        result = matches[0] if matches else None
        return result

    def get_nets_for_component(self, reference: str) -> list[Net]:
        """Find all nets connected to a given component."""
        connected = [
            net for net in self.nets
            if any(pin.component_ref == reference for pin in net.pins)
        ]
        return connected

    def save_json(self, path: Path) -> None:
        """Serialize to JSON file."""
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load_json(cls, path: Path) -> Netlist:
        """Deserialize from JSON file."""
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.model_validate(data)
