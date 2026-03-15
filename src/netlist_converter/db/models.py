"""SQLite table schemas as SQL DDL strings."""

SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS conversions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    llm_model TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 0.0,
    netlist_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversion_id INTEGER NOT NULL REFERENCES conversions(id) ON DELETE CASCADE,
    reference TEXT NOT NULL,
    component_type TEXT NOT NULL,
    value TEXT NOT NULL DEFAULT '',
    footprint TEXT NOT NULL DEFAULT '',
    manufacturer TEXT NOT NULL DEFAULT '',
    part_number TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS nets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversion_id INTEGER NOT NULL REFERENCES conversions(id) ON DELETE CASCADE,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS net_pins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    net_id INTEGER NOT NULL REFERENCES nets(id) ON DELETE CASCADE,
    component_ref TEXT NOT NULL,
    pin TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_components_conversion ON components(conversion_id);
CREATE INDEX IF NOT EXISTS idx_nets_conversion ON nets(conversion_id);
CREATE INDEX IF NOT EXISTS idx_net_pins_net ON net_pins(net_id);
"""
