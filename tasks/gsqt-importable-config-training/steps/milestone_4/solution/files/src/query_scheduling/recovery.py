"""Recovery schema migration and claimability reporting."""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from collections import defaultdict
from typing import Any


DEFAULT_NOW = dt.datetime(2026, 1, 1, 12, 0, 0)


def _configure(connection: sqlite3.Connection) -> None:
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}


def _has_table(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _add_column_if_missing(
    connection: sqlite3.Connection, table: str, column: str, definition: str
) -> None:
    if column not in _columns(connection, table):
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def ensure_recovery_schema(query_engine: sqlite3.Connection) -> None:
    """Upgrade a legacy query database with recovery metadata in place."""
    _configure(query_engine)
    _add_column_if_missing(query_engine, "query_schedule", "payload_json", "TEXT DEFAULT '{}'")
    _add_column_if_missing(query_engine, "query_schedule", "completed_at", "TEXT")
    _add_column_if_missing(query_engine, "query_schedule", "lease_version", "INTEGER DEFAULT 0")
    query_engine.execute(
        """
        CREATE TABLE IF NOT EXISTS query_dependencies (
            query_id INTEGER NOT NULL,
            depends_on_id INTEGER NOT NULL,
            PRIMARY KEY (query_id, depends_on_id)
        )
        """
    )
    if _has_table(query_engine, "query_lock_events"):
        _add_column_if_missing(
            query_engine,
            "query_lock_events",
            "metadata_json",
            "TEXT NOT NULL DEFAULT '{}'",
        )
    query_engine.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_query_recovery_window
        ON query_schedule(country, pod_id, priority, scheduled_execution_date, id)
        WHERE deletion_date IS NULL
        """
    )
    query_engine.commit()


def _norm(text: str | None) -> str | None:
    return text.replace(" ", "T") if text else text


def _parse(text: str | None) -> dt.datetime | None:
    normalized = _norm(text)
    return dt.datetime.fromisoformat(normalized) if normalized else None


def _is_paused(payload_json: str | None) -> bool:
    if not payload_json:
        return False
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return False
    scheduler = payload.get("scheduler") if isinstance(payload, dict) else None
    return isinstance(scheduler, dict) and scheduler.get("paused") is True


def _cycle_ids(dependencies: dict[int, set[int]]) -> set[int]:
    cycles: set[int] = set()
    visiting: set[int] = set()
    visited: set[int] = set()

    def visit(node: int, path: list[int]) -> None:
        if node in visiting:
            start = path.index(node)
            cycles.update(path[start:])
            return
        if node in visited:
            return
        visiting.add(node)
        path.append(node)
        for child in dependencies.get(node, set()):
            visit(child, path)
        path.pop()
        visiting.remove(node)
        visited.add(node)

    for dependency in dependencies:
        visit(dependency, [])
    return cycles


def build_recovery_report(
    query_engine: sqlite3.Connection, now: dt.datetime | None = None
) -> dict[str, Any]:
    """Explain recovery readiness for every scheduled query in the active window."""
    ensure_recovery_schema(query_engine)
    current_time = now or DEFAULT_NOW
    window_end = current_time + dt.timedelta(minutes=10)
    stale_before = current_time - dt.timedelta(minutes=15)
    current_text = current_time.isoformat(timespec="seconds")
    window_end_text = window_end.isoformat(timespec="seconds")

    rows = {
        row["id"]: dict(row)
        for row in query_engine.execute(
            """
            SELECT *
            FROM query_schedule
            WHERE deletion_date IS NULL
            """
        )
    }
    dependency_rows = query_engine.execute(
        "SELECT query_id, depends_on_id FROM query_dependencies"
    ).fetchall()
    dependencies: dict[int, set[int]] = defaultdict(set)
    for row in dependency_rows:
        dependencies[row["query_id"]].add(row["depends_on_id"])
    cycles = _cycle_ids(dependencies)

    paused_ids: list[int] = []
    stale_lock_ids: list[int] = []
    blocked: dict[str, list[int]] = {}
    ready_rows: list[dict[str, Any]] = []

    for query_id, row in rows.items():
        scheduled = _norm(row["scheduled_execution_date"])
        in_window = scheduled is not None and current_text <= scheduled <= window_end_text
        if not in_window or row.get("completed_at") is not None:
            continue

        locked_at = _parse(row.get("locked_at"))
        stale = (
            row.get("human_user_id") is not None
            and locked_at is not None
            and locked_at < stale_before
        )
        if stale:
            stale_lock_ids.append(query_id)

        if _is_paused(row.get("payload_json")):
            paused_ids.append(query_id)
            continue

        unresolved: list[int] = []
        for depends_on_id in sorted(dependencies.get(query_id, set())):
            dependency = rows.get(depends_on_id)
            if (
                dependency is None
                or dependency.get("deletion_date") is not None
                or dependency.get("completed_at") is None
            ):
                unresolved.append(depends_on_id)
        if unresolved:
            blocked[str(query_id)] = unresolved
            continue

        if query_id in cycles:
            continue

        if row.get("human_user_id") is not None and not stale:
            continue
        ready_rows.append(row)

    ready_rows.sort(
        key=lambda row: (
            row["country"],
            -row["priority"],
            _norm(row["scheduled_execution_date"]),
            row["id"],
        )
    )
    ready_by_country: dict[str, list[int]] = defaultdict(list)
    for row in ready_rows:
        ready_by_country[row["country"]].append(row["id"])

    return {
        "schema": {
            "payload_supported": "payload_json" in _columns(query_engine, "query_schedule"),
            "completed_supported": "completed_at" in _columns(query_engine, "query_schedule"),
            "lease_supported": "lease_version" in _columns(query_engine, "query_schedule"),
            "dependencies_supported": _has_table(query_engine, "query_dependencies"),
        },
        "ready_by_country": dict(ready_by_country),
        "blocked_by_dependency": dict(sorted(blocked.items(), key=lambda item: int(item[0]))),
        "cycle_ids": sorted(cycles),
        "paused_ids": sorted(paused_ids),
        "stale_lock_ids": sorted(stale_lock_ids),
    }
