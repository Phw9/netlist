"""Abstract base class for netlist format generators."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from netlist_converter.models import Netlist


class NetlistGenerator(ABC):
    """Base class all netlist format generators must implement."""

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """File extension for this format (e.g. '.cir')."""

    @abstractmethod
    def generate(self, netlist: Netlist) -> str:
        """Convert a Netlist model into a format-specific string."""

    def write(self, netlist: Netlist, output_path: Path) -> Path:
        """Generate and write the netlist to a file."""
        content = self.generate(netlist)
        final_path = output_path.with_suffix(self.file_extension)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        final_path.write_text(content, encoding="utf-8")
        return final_path
