"""Append-only ledger: every change is an immutable row, reports are derived."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .money import Money

SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    day       TEXT NOT NULL,
    category  TEXT NOT NULL,
    amount    INTEGER NOT NULL,     -- minor units, negative = expense
    note      TEXT NOT NULL DEFAULT '',
    currency  TEXT NOT NULL DEFAULT 'USD'
);
CREATE INDEX IF NOT EXISTS idx_entries_day ON entries(day);
CREATE TABLE IF NOT EXISTS limits (
    category TEXT PRIMARY KEY,
    amount   INTEGER NOT NULL
);
"""


@dataclass(slots=True, frozen=True)
class Entry:
    id: int
    day: str
    category: str
    amount: Money
    note: str


class Ledger:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Ledger":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- writes -----------------------------------------------------------
    def add(self, amount: Money, category: str, *, note: str = "", day: str | None = None) -> int:
        day = day or date.today().isoformat()
        try:
            date.fromisoformat(day)
        except ValueError as exc:
            raise ValueError(f"invalid date {day!r}; use YYYY-MM-DD") from exc
        cur = self._conn.execute(
            "INSERT INTO entries (day, category, amount, note, currency) VALUES (?,?,?,?,?)",
            (day, category.strip().lower(), amount.minor, note, amount.currency),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def set_limit(self, category: str, amount: Money) -> None:
        self._conn.execute(
            "INSERT INTO limits (category, amount) VALUES (?,?)"
            " ON CONFLICT(category) DO UPDATE SET amount = excluded.amount",
            (category.strip().lower(), amount.minor),
        )
        self._conn.commit()

    # -- reads ------------------------------------------------------------
    def entries(self, *, month: str | None = None) -> list[Entry]:
        sql, params = "SELECT * FROM entries", ()
        if month:
            sql += " WHERE day LIKE ?"
            params = (f"{month}-%",)
        rows = self._conn.execute(sql + " ORDER BY day, id", params).fetchall()
        return [
            Entry(r["id"], r["day"], r["category"], Money(r["amount"], r["currency"]), r["note"])
            for r in rows
        ]

    def balance(self) -> Money:
        rows = self.entries()
        currency = rows[0].amount.currency if rows else "USD"
        return Money(sum(e.amount.minor for e in rows), currency)

    def by_category(self, *, month: str | None = None) -> dict[str, int]:
        totals: dict[str, int] = {}
        for e in self.entries(month=month):
            totals[e.category] = totals.get(e.category, 0) + e.amount.minor
        return dict(sorted(totals.items(), key=lambda kv: kv[1]))

    def limits(self) -> dict[str, int]:
        return {r["category"]: r["amount"] for r in self._conn.execute("SELECT * FROM limits")}

    def overspent(self, *, month: str | None = None) -> list[tuple[str, Money, Money]]:
        """Returns (category, spent, limit) for categories over their limit."""
        limits, spend = self.limits(), self.by_category(month=month)
        out = []
        for category, cap in limits.items():
            used = -spend.get(category, 0)
            if used > cap:
                out.append((category, Money(used), Money(cap)))
        return out

    def monthly_totals(self) -> dict[str, tuple[int, int]]:
        """month -> (income_minor, expense_minor), expenses positive."""
        totals: dict[str, list[int]] = {}
        for e in self.entries():
            bucket = totals.setdefault(e.day[:7], [0, 0])
            if e.amount.minor >= 0:
                bucket[0] += e.amount.minor
            else:
                bucket[1] += -e.amount.minor
        return {k: (v[0], v[1]) for k, v in sorted(totals.items())}
