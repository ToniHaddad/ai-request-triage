"""SQLite storage for requests."""
from __future__ import annotations

import os
import sqlite3

from .model import Request
from .seed import SEED

COLUMNS = ("team", "office", "title", "description", "per_week", "people", "minutes", "owner",
           "data_class", "success_text", "success_measurable", "existing_tool", "task_kind",
           "consequence", "systems")

SCHEMA = """CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team TEXT, office TEXT, title TEXT, description TEXT,
    per_week REAL, people INTEGER, minutes REAL, owner TEXT,
    data_class TEXT, success_text TEXT, success_measurable INTEGER,
    existing_tool TEXT, task_kind TEXT, consequence TEXT, systems INTEGER)"""


def db_path() -> str:
    return os.environ.get("TRIAGE_DB", "triage.db")


class Store:
    def __init__(self, path: str | None = None, seed: bool = True):
        self.path = path or db_path()
        self.con = sqlite3.connect(self.path, check_same_thread=False)
        self.con.row_factory = sqlite3.Row
        self.con.execute(SCHEMA)
        if seed and not self.con.execute("SELECT 1 FROM requests LIMIT 1").fetchone():
            self.reset()

    def reset(self) -> None:
        self.con.execute("DELETE FROM requests")
        self.con.execute("DELETE FROM sqlite_sequence WHERE name='requests'")
        for row in SEED:
            self.add(row)

    def add(self, row: dict) -> int:
        vals = [int(row[c]) if c == "success_measurable" else row[c] for c in COLUMNS]
        cur = self.con.execute(
            f"INSERT INTO requests ({','.join(COLUMNS)}) VALUES ({','.join('?' * len(COLUMNS))})", vals)
        self.con.commit()
        return cur.lastrowid

    def delete(self, rid: int) -> bool:
        cur = self.con.execute("DELETE FROM requests WHERE id=?", (rid,))
        self.con.commit()
        return cur.rowcount > 0

    def all(self) -> list[Request]:
        out = []
        for r in self.con.execute("SELECT * FROM requests ORDER BY id"):
            d = dict(r)
            d["success_measurable"] = bool(d["success_measurable"])
            out.append(Request(**d))
        return out
