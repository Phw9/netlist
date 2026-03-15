"""Tests for SQLite storage layer."""

from __future__ import annotations

import tempfile
from pathlib import Path

from netlist_converter.db.sqlite_store import SQLiteStore
from netlist_converter.models import Netlist


class TestSQLiteStore:
    def test_save_and_load(self, sample_netlist: Netlist) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = SQLiteStore(db_path)

            cid = store.save_netlist(sample_netlist)
            assert cid >= 1

            loaded = store.get_netlist(cid)
            assert loaded is not None
            assert loaded.component_count == sample_netlist.component_count
            assert loaded.net_count == sample_netlist.net_count

            store.close()

    def test_list_conversions(self, sample_netlist: Netlist) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = SQLiteStore(db_path)

            store.save_netlist(sample_netlist)
            store.save_netlist(sample_netlist)

            records = store.list_conversions()
            assert len(records) == 2
            assert records[0].source_file == "test_circuit.png"

            store.close()

    def test_delete_conversion(self, sample_netlist: Netlist) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = SQLiteStore(db_path)

            cid = store.save_netlist(sample_netlist)
            assert store.delete_conversion(cid) is True
            assert store.get_netlist(cid) is None
            assert store.delete_conversion(999) is False

            store.close()

    def test_nonexistent_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = SQLiteStore(db_path)

            assert store.get_netlist(9999) is None

            store.close()
