"""SQLite storage for structured netlist data."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from netlist_converter.db.models import SCHEMA_SQL
from netlist_converter.models import Netlist


@dataclass
class ConversionRecord:
    """Summary of a stored conversion."""

    id: int
    source_file: str
    created_at: str
    llm_model: str
    confidence: float


class SQLiteStore:
    """Synchronous SQLite storage for netlist conversion results."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()

    def save_netlist(self, netlist: Netlist) -> int:
        """Persist a netlist and return its conversion ID."""
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO conversions (source_file, llm_model, confidence, netlist_json) "
            "VALUES (?, ?, ?, ?)",
            (
                netlist.metadata.source_file,
                netlist.metadata.llm_model,
                netlist.metadata.confidence,
                netlist.model_dump_json(),
            ),
        )
        conversion_id = cur.lastrowid

        for comp in netlist.components:
            cur.execute(
                "INSERT INTO components "
                "(conversion_id, reference, component_type, value, footprint, "
                "manufacturer, part_number, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    conversion_id,
                    comp.reference,
                    comp.component_type.value,
                    comp.value,
                    comp.footprint,
                    comp.manufacturer,
                    comp.part_number,
                    comp.description,
                ),
            )

        for net in netlist.nets:
            cur.execute(
                "INSERT INTO nets (conversion_id, name) VALUES (?, ?)",
                (conversion_id, net.name),
            )
            net_id = cur.lastrowid
            for pin in net.pins:
                cur.execute(
                    "INSERT INTO net_pins (net_id, component_ref, pin) VALUES (?, ?, ?)",
                    (net_id, pin.component_ref, pin.pin),
                )

        self._conn.commit()
        return conversion_id

    def get_netlist(self, conversion_id: int) -> Netlist | None:
        """Load a netlist by conversion ID."""
        row = self._conn.execute(
            "SELECT netlist_json FROM conversions WHERE id = ?",
            (conversion_id,),
        ).fetchone()

        if row is None:
            return None

        data = json.loads(row["netlist_json"])
        return Netlist.model_validate(data)

    def list_conversions(self, limit: int = 50) -> list[ConversionRecord]:
        """Return recent conversion records."""
        rows = self._conn.execute(
            "SELECT id, source_file, created_at, llm_model, confidence "
            "FROM conversions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()

        return [
            ConversionRecord(
                id=r["id"],
                source_file=r["source_file"],
                created_at=r["created_at"],
                llm_model=r["llm_model"],
                confidence=r["confidence"],
            )
            for r in rows
        ]

    def delete_conversion(self, conversion_id: int) -> bool:
        """Delete a conversion and its related data. Returns True if found."""
        cur = self._conn.execute(
            "DELETE FROM conversions WHERE id = ?", (conversion_id,)
        )
        self._conn.commit()
        return cur.rowcount > 0

    def close(self) -> None:
        self._conn.close()
