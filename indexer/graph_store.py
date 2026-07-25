from pathlib import Path
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class Symbol:
    file_id: int
    name: str
    qualified_name: str
    symbol_type: str
    start_line: int
    end_line: int
    signature: str | None = None
    docstring: str | None = None


@dataclass
class Edge:
    from_id: int
    to_name: str
    edge_type: str
    to_file: str | None = None


class GraphStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")

    def init_schema(self) -> None:
        self.conn.executescript("""
CREATE TABLE IF NOT EXISTS files (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    path        TEXT NOT NULL UNIQUE,
    language    TEXT NOT NULL,
    hash        TEXT NOT NULL,
    indexed_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS symbols (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id        INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    name           TEXT NOT NULL,
    qualified_name TEXT NOT NULL,
    symbol_type    TEXT NOT NULL,
    start_line     INTEGER NOT NULL,
    end_line       INTEGER NOT NULL,
    signature      TEXT,
    docstring      TEXT
);

CREATE TABLE IF NOT EXISTS edges (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    from_id   INTEGER NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    to_name   TEXT NOT NULL,
    to_file   TEXT,
    edge_type TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_symbols_name      ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_symbols_file      ON symbols(file_id);
CREATE INDEX IF NOT EXISTS idx_symbols_qname     ON symbols(qualified_name);
CREATE INDEX IF NOT EXISTS idx_edges_from        ON edges(from_id);
CREATE INDEX IF NOT EXISTS idx_edges_to_name     ON edges(to_name);
CREATE INDEX IF NOT EXISTS idx_files_path        ON files(path);
""")
        self.conn.commit()

    def upsert_file(self, path: str, language: str, file_hash: str) -> int:
        indexed_at = datetime.now(timezone.utc).isoformat()
        cur = self.conn.execute(
            "INSERT OR REPLACE INTO files (path, language, hash, indexed_at) VALUES (?, ?, ?, ?)",
            (path, language, file_hash, indexed_at),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def get_file_hash(self, path: str) -> str | None:
        row = self.conn.execute("SELECT hash FROM files WHERE path = ?", (path,)).fetchone()
        return None if row is None else str(row["hash"])

    def insert_symbols(self, symbols: list[Symbol]) -> dict[str, int]:
        mapping: dict[str, int] = {}
        for symbol in symbols:
            cur = self.conn.execute(
                "INSERT INTO symbols (file_id, name, qualified_name, symbol_type, start_line, end_line, signature, docstring) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (symbol.file_id, symbol.name, symbol.qualified_name, symbol.symbol_type, symbol.start_line, symbol.end_line, symbol.signature, symbol.docstring),
            )
            mapping[symbol.qualified_name] = int(cur.lastrowid)
        self.conn.commit()
        return mapping

    def insert_edges(self, edges: list[Edge]) -> None:
        self.conn.executemany(
            "INSERT INTO edges (from_id, to_name, to_file, edge_type) VALUES (?, ?, ?, ?)",
            [(edge.from_id, edge.to_name, edge.to_file, edge.edge_type) for edge in edges],
        )
        self.conn.commit()

    def delete_file_data(self, file_id: int) -> None:
        self.conn.execute("DELETE FROM symbols WHERE file_id = ?", (file_id,))
        self.conn.commit()

    def get_symbol(self, name: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT s.*, f.path AS file FROM symbols s JOIN files f ON s.file_id = f.id WHERE s.name = ? OR s.qualified_name = ? ORDER BY s.qualified_name",
            (name, name),
        ).fetchall()
        if not rows:
            rows = self.conn.execute(
                "SELECT s.*, f.path AS file FROM symbols s JOIN files f ON s.file_id = f.id WHERE s.name LIKE ? OR s.qualified_name LIKE ? ORDER BY s.qualified_name",
                (f"%{name}%", f"%{name}%"),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_file_symbols(self, file_path: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT s.*, f.path AS file FROM symbols s JOIN files f ON s.file_id = f.id WHERE f.path = ? ORDER BY s.start_line, s.qualified_name",
            (file_path,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_file_imports(self, file_path: str) -> dict:
        file_row = self.conn.execute("SELECT id, path FROM files WHERE path = ?", (file_path,)).fetchone()
        if file_row is None:
            return {}
        rows = self.conn.execute(
            "SELECT e.* FROM edges e JOIN symbols s ON e.from_id = s.id WHERE s.file_id = ? AND e.edge_type IN (?, ?)",
            (file_row["id"], "imports", "inherits"),
        ).fetchall()
        return {"file": file_path, "edges": [dict(row) for row in rows]}

    def get_callers(self, function_name: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT s.qualified_name AS symbol, f.path AS file, s.start_line AS line, e.to_name FROM edges e JOIN symbols s ON e.from_id = s.id JOIN files f ON s.file_id = f.id WHERE e.edge_type = ? AND (e.to_name = ? OR e.to_name LIKE ?) ORDER BY f.path, s.start_line",
            ("calls", function_name, f"%.{function_name}"),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_stats(self) -> dict:
        return {
            "files": self.conn.execute("SELECT COUNT(*) AS n FROM files").fetchone()["n"],
            "symbols": self.conn.execute("SELECT COUNT(*) AS n FROM symbols").fetchone()["n"],
            "edges": self.conn.execute("SELECT COUNT(*) AS n FROM edges").fetchone()["n"],
        }
