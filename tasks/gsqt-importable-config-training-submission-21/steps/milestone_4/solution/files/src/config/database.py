"""Lazy database configuration for the stripped-down GSQT scheduler."""

from __future__ import annotations

import os
import sqlite3
from typing import Any


_query_engine: sqlite3.Connection | None = None
_query_dsn: str | None = None
_node_engine: sqlite3.Connection | None = None
_node_dsn: str | None = None


def _connect_from_env(variable_name: str) -> sqlite3.Connection:
    dsn = os.environ.get(variable_name)
    if not dsn:
        raise RuntimeError(f"{variable_name} must be set before opening a database connection")

    connection = sqlite3.connect(dsn, uri=dsn.startswith("file:"))
    connection.row_factory = sqlite3.Row
    return connection


def get_query_engine() -> sqlite3.Connection:
    global _query_engine, _query_dsn
    dsn = os.environ.get("GSQT_QUERY_DSN")
    if not dsn:
        raise RuntimeError("GSQT_QUERY_DSN must be set before opening a database connection")
    if _query_engine is None or dsn != _query_dsn:
        if _query_engine is not None:
            _query_engine.close()
        _query_engine = _connect_from_env("GSQT_QUERY_DSN")
        _query_dsn = dsn
    return _query_engine


def get_node_engine() -> sqlite3.Connection:
    global _node_engine, _node_dsn
    dsn = os.environ.get("GSQT_NODE_DSN")
    if not dsn:
        raise RuntimeError("GSQT_NODE_DSN must be set before opening a database connection")
    if _node_engine is None or dsn != _node_dsn:
        if _node_engine is not None:
            _node_engine.close()
        _node_engine = _connect_from_env("GSQT_NODE_DSN")
        _node_dsn = dsn
    return _node_engine


class DatabaseOperations:
    """Small SQL helper used by services in this task."""

    @staticmethod
    def update_by_id(connection: sqlite3.Connection, table: str, record_id: int, **fields: Any) -> None:
        if not fields:
            return
        assignments = ", ".join(f"{column} = ?" for column in fields)
        values = list(fields.values())
        values.append(record_id)
        connection.execute(f"UPDATE {table} SET {assignments} WHERE id = ?", values)
        connection.commit()
