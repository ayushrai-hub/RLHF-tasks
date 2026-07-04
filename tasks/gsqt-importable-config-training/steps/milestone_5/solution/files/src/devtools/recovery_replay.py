"""Recovery replay CLI for scheduler readiness diagnostics."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
from typing import Any

from src.query_scheduling.recovery import build_recovery_report, ensure_recovery_schema
from src.testing import recovery_scenarios


DEFAULT_NOW = dt.datetime(2026, 1, 1, 12, 0, 0)


def _norm(text: str | None) -> str | None:
    return text.replace(" ", "T") if text else text


def _metadata_rows(query_engine: sqlite3.Connection) -> list[dict[str, Any]]:
    if not query_engine.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'query_lock_events'"
    ).fetchone():
        return []
    rows = query_engine.execute(
        """
        SELECT metadata_json
        FROM query_lock_events
        WHERE action = 'recovery_claim'
        ORDER BY id
        """
    ).fetchall()
    return [json.loads(row["metadata_json"]) for row in rows]


def _insert_event(
    query_engine: sqlite3.Connection,
    query_id: int,
    human_user_id: int,
    thread_id: int | None,
    event_time: str,
    previous_human_user_id: int | None,
    previous_locked_at: str | None,
    ready_before: list[int],
) -> None:
    if not query_engine.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'query_lock_events'"
    ).fetchone():
        return
    metadata_json = json.dumps(
        {"source": "recovery_replay", "ready_before": ready_before},
        sort_keys=True,
    )
    query_engine.execute(
        """
        INSERT INTO query_lock_events
            (query_schedule_id, human_user_id, thread_id, action, event_time,
             previous_human_user_id, previous_locked_at, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            query_id,
            human_user_id,
            thread_id,
            "recovery_claim",
            event_time,
            previous_human_user_id,
            previous_locked_at,
            metadata_json,
        ),
    )


def claim_next_ready(
    query_engine: sqlite3.Connection,
    country_node: str,
    human_user: dict[str, Any],
    now: dt.datetime | None = None,
    thread_id: int | None = None,
) -> tuple[dict[str, Any] | None, bool]:
    """Claim the next recovery-ready query with a transaction-first write lock."""
    ensure_recovery_schema(query_engine)
    current_time = now or DEFAULT_NOW
    window_end = current_time + dt.timedelta(minutes=10)
    stale_before = current_time - dt.timedelta(minutes=15)
    now_text = current_time.isoformat(timespec="seconds")
    window_end_text = window_end.isoformat(timespec="seconds")
    stale_before_text = stale_before.isoformat(timespec="seconds")

    while True:
        report = build_recovery_report(query_engine, now=current_time)
        ready_before = list(report["ready_by_country"].get(country_node, []))
        if not ready_before:
            return None, True
        query_id = ready_before[0]
        if query_engine.in_transaction:
            query_engine.commit()
        query_engine.execute("BEGIN IMMEDIATE")
        row = query_engine.execute(
            "SELECT * FROM query_schedule WHERE id = ?",
            (query_id,),
        ).fetchone()
        if row is None:
            query_engine.rollback()
            continue
        cursor = query_engine.execute(
            """
            UPDATE query_schedule
            SET human_user_id = ?,
                locked_at = ?,
                locked_by_thread = ?,
                lease_version = COALESCE(lease_version, 0) + 1
            WHERE id = ?
              AND deletion_date IS NULL
              AND completed_at IS NULL
              AND replace(scheduled_execution_date, ' ', 'T') >= ?
              AND replace(scheduled_execution_date, ' ', 'T') <= ?
              AND (
                    human_user_id IS NULL
                    OR (locked_at IS NOT NULL AND replace(locked_at, ' ', 'T') < ?)
                  )
            """,
            (
                human_user["human_user_id"],
                now_text,
                thread_id,
                query_id,
                now_text,
                window_end_text,
                stale_before_text,
            ),
        )
        if cursor.rowcount == 1:
            _insert_event(
                query_engine,
                query_id,
                human_user["human_user_id"],
                thread_id,
                now_text,
                row["human_user_id"],
                row["locked_at"],
                ready_before,
            )
            query_engine.commit()
            return dict(row), False
        query_engine.rollback()


def run_recovery_replay(
    query_engine: sqlite3.Connection | None = None, now: dt.datetime | None = None
) -> dict[str, Any]:
    current_time = now or DEFAULT_NOW
    connection = query_engine or recovery_scenarios.build_recovery_query_db(now=current_time)
    initial_report = build_recovery_report(connection, now=current_time)
    first, first_camo = claim_next_ready(
        connection,
        "DE",
        {"human_user_id": 42, "pod_id": 3},
        now=current_time,
        thread_id=91,
    )
    second, second_camo = claim_next_ready(
        connection,
        "FR",
        {"human_user_id": 42, "pod_id": 3},
        now=current_time,
        thread_id=92,
    )
    final_report = build_recovery_report(connection, now=current_time)
    return {
        "initial_ready": initial_report["ready_by_country"],
        "initial_blocked": initial_report["blocked_by_dependency"],
        "initial_cycles": initial_report["cycle_ids"],
        "initial_paused": initial_report["paused_ids"],
        "claimed_ids": [
            first["id"] if first is not None else None,
            second["id"] if second is not None else None,
        ],
        "camo_flags": [first_camo, second_camo],
        "final_ready": final_report["ready_by_country"],
        "final_stale_locks": final_report["stale_lock_ids"],
        "event_metadata": _metadata_rows(connection),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)

    report = run_recovery_replay()
    if args.json:
        print(json.dumps(report, sort_keys=True))
    else:
        for key, value in report.items():
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
