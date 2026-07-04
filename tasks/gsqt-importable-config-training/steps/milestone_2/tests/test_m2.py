"""Milestone 2 verifier for injected database dependencies."""

from __future__ import annotations

import datetime as dt
import importlib
import os
import sqlite3
import sys
from pathlib import Path

import pytest


APP_DIR = Path(os.environ.get("APP_DIR", "/app"))


def clear_src_modules() -> None:
    for name in list(sys.modules):
        if name == "src" or name.startswith("src."):
            del sys.modules[name]


def make_query_db(
    now: dt.datetime,
    database: str | Path = ":memory:",
    include_events: bool = False,
) -> sqlite3.Connection:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE query_schedule (
            id INTEGER PRIMARY KEY,
            pod_id INTEGER NOT NULL,
            country TEXT NOT NULL,
            human_user_id INTEGER,
            scheduled_execution_date TEXT NOT NULL,
            deletion_date TEXT,
            priority INTEGER NOT NULL DEFAULT 0,
            locked_at TEXT,
            locked_by_thread INTEGER
        );
        CREATE TABLE query_schedule_steps (
            id INTEGER PRIMARY KEY,
            query_schedule_id INTEGER NOT NULL,
            position INTEGER,
            type TEXT NOT NULL,
            value TEXT,
            completed_date TEXT,
            url TEXT,
            title TEXT
        );
        CREATE TABLE human_users (
            id INTEGER PRIMARY KEY,
            last_locked TEXT
        );
        """
    )
    if include_events:
        connection.executescript(
            """
            CREATE TABLE query_lock_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_schedule_id INTEGER,
                human_user_id INTEGER,
                thread_id INTEGER,
                action TEXT NOT NULL,
                event_time TEXT NOT NULL,
                previous_human_user_id INTEGER,
                previous_locked_at TEXT
            );
            """
        )
    rows = [
        (1, 3, "DE", None, now + dt.timedelta(minutes=2), None, 10, None, None),
        (2, 3, "DE", 99, now + dt.timedelta(minutes=1), None, 99, now, 5),
        (3, 3, "FR", None, now + dt.timedelta(minutes=1), None, 80, None, None),
        (4, 3, "DE", None, now + dt.timedelta(minutes=30), None, 90, None, None),
        (5, 3, "DE", None, now + dt.timedelta(minutes=3), "deleted", 100, None, None),
        (6, 4, "DE", None, now + dt.timedelta(minutes=1), None, 100, None, None),
        (7, 3, "DE", None, now + dt.timedelta(minutes=4), None, 50, None, None),
        (8, 3, "DE", 88, now + dt.timedelta(minutes=1), None, 5, now - dt.timedelta(minutes=30), 6),
        (17, 3, "DE", None, now - dt.timedelta(minutes=5), None, 200, None, None),
    ]
    connection.executemany(
        """
        INSERT INTO query_schedule
            (id, pod_id, country, human_user_id, scheduled_execution_date, deletion_date,
             priority, locked_at, locked_by_thread)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row_id,
                pod_id,
                country,
                user_id,
                scheduled.isoformat(timespec="seconds"),
                deleted,
                priority,
                locked_at.isoformat(timespec="seconds") if locked_at else None,
                locked_by_thread,
            )
            for (
                row_id,
                pod_id,
                country,
                user_id,
                scheduled,
                deleted,
                priority,
                locked_at,
                locked_by_thread,
            ) in rows
        ],
    )
    connection.executemany(
        """
        INSERT INTO query_schedule_steps
            (query_schedule_id, position, type, value, completed_date, url, title)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (7, 2, "click_result", "any", None, None, None),
            (7, 1, "google_search", "best pasta berlin", None, None, None),
        ],
    )
    connection.execute("INSERT INTO human_users (id, last_locked) VALUES (42, 'locked')")
    connection.commit()
    return connection


class RacingFetchCursor:
    def __init__(self, cursor: sqlite3.Cursor, connection: "RacingClaimConnection"):
        self._cursor = cursor
        self._connection = connection

    def _row_id(self, row: sqlite3.Row) -> int:
        try:
            return row["id"]
        except (IndexError, KeyError):
            return self._connection.race_target_id

    def _apply_race(self, row: sqlite3.Row | None) -> None:
        if row is None or self._connection.race_applied:
            return
        self._connection.race_applied = True
        sqlite3.Connection.execute(
            self._connection,
            """
            UPDATE query_schedule
            SET human_user_id = ?, locked_at = ?, locked_by_thread = ?
            WHERE id = ?
            """,
            (
                77,
                self._connection.race_time.isoformat(timespec="seconds"),
                99,
                self._row_id(row),
            ),
        )
        sqlite3.Connection.commit(self._connection)

    def fetchone(self):
        row = self._cursor.fetchone()
        self._apply_race(row)
        return row

    def fetchall(self):
        rows = self._cursor.fetchall()
        self._apply_race(rows[0] if rows else None)
        return rows

    def fetchmany(self, size: int | None = None):
        rows = self._cursor.fetchmany() if size is None else self._cursor.fetchmany(size)
        self._apply_race(rows[0] if rows else None)
        return rows

    def __iter__(self):
        while True:
            row = self._cursor.fetchone()
            if row is None:
                return
            self._apply_race(row)
            yield row

    def __getattr__(self, name: str):
        return getattr(self._cursor, name)


class RacingClaimConnection(sqlite3.Connection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.race_applied = False
        self.race_time = dt.datetime(2026, 1, 1, 12, 0, 1)
        self.race_target_id = 7

    def execute(self, sql: str, parameters=(), /):
        cursor = super().execute(sql, parameters)
        normalized = " ".join(sql.upper().split())
        if (
            normalized.startswith("SELECT")
            and " FROM QUERY_SCHEDULE " in f" {normalized} "
            and " ORDER BY " in f" {normalized} "
        ):
            return RacingFetchCursor(cursor, self)
        return cursor


def make_racing_query_db(now: dt.datetime) -> RacingClaimConnection:
    connection = sqlite3.connect(":memory:", factory=RacingClaimConnection)
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE query_schedule (
            id INTEGER PRIMARY KEY,
            pod_id INTEGER NOT NULL,
            country TEXT NOT NULL,
            human_user_id INTEGER,
            scheduled_execution_date TEXT NOT NULL,
            deletion_date TEXT,
            priority INTEGER NOT NULL DEFAULT 0,
            locked_at TEXT,
            locked_by_thread INTEGER
        );
        CREATE TABLE query_lock_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_schedule_id INTEGER,
            human_user_id INTEGER,
            thread_id INTEGER,
            action TEXT NOT NULL,
            event_time TEXT NOT NULL,
            previous_human_user_id INTEGER,
            previous_locked_at TEXT
        );
        """
    )
    connection.executemany(
        """
        INSERT INTO query_schedule
            (id, pod_id, country, human_user_id, scheduled_execution_date,
             deletion_date, priority, locked_at, locked_by_thread)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                7,
                3,
                "DE",
                None,
                (now + dt.timedelta(minutes=1)).isoformat(timespec="seconds"),
                None,
                50,
                None,
                None,
            ),
            (
                12,
                3,
                "DE",
                None,
                (now + dt.timedelta(minutes=2)).isoformat(timespec="seconds"),
                None,
                40,
                None,
                None,
            ),
        ],
    )
    connection.commit()
    return connection


def make_single_claim_db(database: Path, now: dt.datetime) -> None:
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE query_schedule (
            id INTEGER PRIMARY KEY,
            pod_id INTEGER NOT NULL,
            country TEXT NOT NULL,
            human_user_id INTEGER,
            scheduled_execution_date TEXT NOT NULL,
            deletion_date TEXT,
            priority INTEGER NOT NULL DEFAULT 0,
            locked_at TEXT,
            locked_by_thread INTEGER
        );
        """
    )
    connection.executemany(
        """
        INSERT INTO query_schedule
            (id, pod_id, country, human_user_id, scheduled_execution_date,
             deletion_date, priority, locked_at, locked_by_thread)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                11,
                3,
                "DE",
                None,
                (now + dt.timedelta(minutes=1)).isoformat(timespec="seconds"),
                None,
                70,
                None,
                None,
            ),
            (
                12,
                3,
                "DE",
                None,
                (now + dt.timedelta(minutes=2)).isoformat(timespec="seconds"),
                None,
                60,
                None,
                None,
            ),
        ],
    )
    connection.commit()
    connection.close()


def make_node_db(database: str | Path = ":memory:") -> sqlite3.Connection:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE nodes (
            uuid TEXT PRIMARY KEY,
            currently_online TEXT NOT NULL,
            country TEXT NOT NULL
        );
        CREATE TABLE nodes_to_human_users (
            node_uuid TEXT NOT NULL,
            human_user_id INTEGER NOT NULL
        );
        INSERT INTO nodes VALUES ('node-a', 'TRUE', 'DE');
        INSERT INTO nodes VALUES ('node-b', 'FALSE', 'FR');
        INSERT INTO nodes_to_human_users VALUES ('node-a', 42);
        INSERT INTO nodes_to_human_users VALUES ('node-a', 42);
        INSERT INTO nodes_to_human_users VALUES ('node-a', 44);
        INSERT INTO nodes_to_human_users VALUES ('node-b', 43);
        """
    )
    return connection


def make_legacy_step_db_without_position() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE query_schedule_steps (
            id INTEGER PRIMARY KEY,
            query_schedule_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            value TEXT,
            completed_date TEXT,
            url TEXT,
            title TEXT
        );
        INSERT INTO query_schedule_steps
            (id, query_schedule_id, type, value, completed_date, url, title)
        VALUES
            (20, 900, 'click_result', 'any', NULL, NULL, NULL),
            (19, 900, 'google_search', 'old fixture', NULL, NULL, NULL);
        """
    )
    return connection


def make_nullable_position_step_db() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE query_schedule_steps (
            id INTEGER PRIMARY KEY,
            query_schedule_id INTEGER NOT NULL,
            position INTEGER,
            type TEXT NOT NULL,
            value TEXT,
            completed_date TEXT,
            url TEXT,
            title TEXT
        );
        INSERT INTO query_schedule_steps
            (id, query_schedule_id, position, type, value, completed_date, url, title)
        VALUES
            (31, 901, NULL, 'archive_result', 'done', NULL, NULL, NULL),
            (30, 901, 2, 'click_result', 'any', NULL, NULL, NULL),
            (29, 901, 1, 'google_search', 'mixed positions', NULL, NULL, NULL);
        """
    )
    return connection


class TestMilestone2:
    def test_scheduler_locks_earliest_matching_query_with_injected_db(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """QueryScheduler uses an injected DB to claim the earliest matching query."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        monkeypatch.delenv("GSQT_QUERY_DSN", raising=False)
        clear_src_modules()
        scheduler_module = importlib.import_module("src.query_scheduling.scheduler")

        now = dt.datetime(2026, 1, 1, 12, 0, 0)
        connection = make_query_db(now)
        scheduler = scheduler_module.QueryScheduler(query_engine=connection)

        selected, camo = scheduler.get_and_lock_query(
            "DE", {"human_user_id": 42, "pod_id": 3}, now=now, thread_id=12
        )

        assert camo is False
        assert selected["id"] == 7
        claimed, locked_at, locked_by_thread = connection.execute(
            "SELECT human_user_id, locked_at, locked_by_thread FROM query_schedule WHERE id = 7"
        ).fetchone()
        priority, scheduled, pod_id, country = connection.execute(
            """
            SELECT priority, scheduled_execution_date, pod_id, country
            FROM query_schedule
            WHERE id = 7
            """
        ).fetchone()
        locked_other = connection.execute(
            "SELECT human_user_id FROM query_schedule WHERE id = 2"
        ).fetchone()[0]
        assert claimed == 42
        assert locked_at == now.isoformat(timespec="seconds")
        assert locked_by_thread == 12
        assert (priority, scheduled, pod_id, country) == (
            50,
            (now + dt.timedelta(minutes=4)).isoformat(timespec="seconds"),
            3,
            "DE",
        )
        assert locked_other == 99

    def test_scheduler_uses_scheduled_date_tiebreaker_for_equal_priority(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Equal-priority candidates are ordered by scheduled date before id."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        monkeypatch.delenv("GSQT_QUERY_DSN", raising=False)
        clear_src_modules()
        scheduler_module = importlib.import_module("src.query_scheduling.scheduler")

        now = dt.datetime(2026, 1, 1, 12, 0, 0)
        connection = make_query_db(now)
        connection.execute(
            """
            INSERT INTO query_schedule
                (id, pod_id, country, human_user_id, scheduled_execution_date,
                 deletion_date, priority, locked_at, locked_by_thread)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                9,
                3,
                "DE",
                None,
                (now + dt.timedelta(minutes=3)).isoformat(timespec="seconds"),
                None,
                50,
                None,
                None,
            ),
        )
        connection.commit()
        scheduler = scheduler_module.QueryScheduler(query_engine=connection)

        selected, camo = scheduler.get_and_lock_query(
            "DE", {"human_user_id": 42, "pod_id": 3}, now=now
        )

        assert camo is False
        assert selected["id"] == 9

    def test_scheduler_uses_id_tiebreaker_for_equal_priority_and_date(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Equal-priority candidates with the same scheduled date are ordered by id."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        monkeypatch.delenv("GSQT_QUERY_DSN", raising=False)
        clear_src_modules()
        scheduler_module = importlib.import_module("src.query_scheduling.scheduler")

        now = dt.datetime(2026, 1, 1, 12, 0, 0)
        connection = make_query_db(now)
        scheduled = (now + dt.timedelta(minutes=3)).isoformat(timespec="seconds")
        connection.executemany(
            """
            INSERT INTO query_schedule
                (id, pod_id, country, human_user_id, scheduled_execution_date,
                 deletion_date, priority, locked_at, locked_by_thread)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (10, 3, "DE", None, scheduled, None, 60, None, None),
                (9, 3, "DE", None, scheduled, None, 60, None, None),
            ],
        )
        connection.commit()
        scheduler = scheduler_module.QueryScheduler(query_engine=connection)

        selected, camo = scheduler.get_and_lock_query(
            "DE", {"human_user_id": 42, "pod_id": 3}, now=now
        )

        assert camo is False
        assert selected["id"] == 9

    def test_scheduler_can_reclaim_stale_locks(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """QueryScheduler treats locks older than the TTL as claimable."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        monkeypatch.delenv("GSQT_QUERY_DSN", raising=False)
        clear_src_modules()
        scheduler_module = importlib.import_module("src.query_scheduling.scheduler")

        now = dt.datetime(2026, 1, 1, 12, 0, 0)
        connection = make_query_db(now)
        connection.execute("UPDATE query_schedule SET priority = 120 WHERE id = 8")
        connection.commit()
        scheduler = scheduler_module.QueryScheduler(query_engine=connection)

        selected, camo = scheduler.get_and_lock_query(
            "DE", {"human_user_id": 42, "pod_id": 3}, now=now, thread_id=13
        )

        assert camo is False
        assert selected["id"] == 8
        row = connection.execute(
            "SELECT human_user_id, locked_at, locked_by_thread FROM query_schedule WHERE id = 8"
        ).fetchone()
        assert tuple(row) == (42, now.isoformat(timespec="seconds"), 13)

    def test_scheduler_normalizes_legacy_datetime_strings(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Space-separated datetimes compare like ISO datetimes, not plain strings."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        monkeypatch.delenv("GSQT_QUERY_DSN", raising=False)
        clear_src_modules()
        scheduler_module = importlib.import_module("src.query_scheduling.scheduler")

        now = dt.datetime(2026, 1, 1, 12, 0, 0)
        connection = make_query_db(now)
        connection.execute(
            """
            INSERT INTO query_schedule
                (id, pod_id, country, human_user_id, scheduled_execution_date,
                 deletion_date, priority, locked_at, locked_by_thread)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                13,
                3,
                "DE",
                None,
                (now + dt.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S"),
                None,
                85,
                None,
                None,
            ),
        )
        connection.commit()
        scheduler = scheduler_module.QueryScheduler(query_engine=connection)

        selected, camo = scheduler.get_and_lock_query(
            "DE", {"human_user_id": 42, "pod_id": 3}, now=now, thread_id=17
        )

        assert camo is False
        assert selected["id"] == 13
        assert connection.execute(
            "SELECT locked_at FROM query_schedule WHERE id = 13"
        ).fetchone()[0] == now.isoformat(timespec="seconds")

        connection.executemany(
            """
            INSERT INTO query_schedule
                (id, pod_id, country, human_user_id, scheduled_execution_date,
                 deletion_date, priority, locked_at, locked_by_thread)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    15,
                    3,
                    "DE",
                    98,
                    (now + dt.timedelta(minutes=1)).isoformat(timespec="seconds"),
                    None,
                    95,
                    (now - dt.timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S"),
                    6,
                ),
                (
                    16,
                    3,
                    "DE",
                    99,
                    (now + dt.timedelta(minutes=1)).isoformat(timespec="seconds"),
                    None,
                    99,
                    (now - dt.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S"),
                    7,
                ),
            ],
        )
        connection.commit()

        reclaimed, reclaim_camo = scheduler.get_and_lock_query(
            "DE", {"human_user_id": 44, "pod_id": 3}, now=now, thread_id=18
        )

        fresh_locked = connection.execute(
            "SELECT human_user_id, locked_at, locked_by_thread FROM query_schedule WHERE id = 16"
        ).fetchone()
        stale_reclaimed = connection.execute(
            "SELECT human_user_id, locked_at, locked_by_thread FROM query_schedule WHERE id = 15"
        ).fetchone()
        assert reclaim_camo is False
        assert reclaimed["id"] == 15
        assert tuple(fresh_locked) == (
            99,
            (now - dt.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S"),
            7,
        )
        assert tuple(stale_reclaimed) == (44, now.isoformat(timespec="seconds"), 18)

    def test_scheduler_retries_next_candidate_after_row_locked_during_claim(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A row locked after selection is not stolen, and the next candidate is tried."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        monkeypatch.delenv("GSQT_QUERY_DSN", raising=False)
        clear_src_modules()
        scheduler_module = importlib.import_module("src.query_scheduling.scheduler")

        now = dt.datetime(2026, 1, 1, 12, 0, 0)
        connection = make_racing_query_db(now)
        scheduler = scheduler_module.QueryScheduler(query_engine=connection)

        selected, camo = scheduler.get_and_lock_query(
            "DE", {"human_user_id": 42, "pod_id": 3}, now=now, thread_id=14
        )

        raced_row = connection.execute(
            "SELECT human_user_id, locked_at, locked_by_thread FROM query_schedule WHERE id = 7"
        ).fetchone()
        fallback_row = connection.execute(
            "SELECT human_user_id, locked_at, locked_by_thread FROM query_schedule WHERE id = 12"
        ).fetchone()
        events = connection.execute(
            """
            SELECT query_schedule_id, action, human_user_id, thread_id
            FROM query_lock_events
            ORDER BY id
            """
        ).fetchall()
        assert camo is False
        assert selected["id"] == 12
        assert tuple(raced_row) == (
            77,
            connection.race_time.isoformat(timespec="seconds"),
            99,
        )
        assert tuple(fallback_row) == (42, now.isoformat(timespec="seconds"), 14)
        assert [tuple(row) for row in events] == [
            (7, "race_miss", 42, 14),
            (12, "claim", 42, 14),
        ]

    def test_file_backed_schedulers_do_not_double_claim_same_row(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Separate SQLite connections claim distinct rows rather than double-claiming."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        monkeypatch.delenv("GSQT_QUERY_DSN", raising=False)
        clear_src_modules()
        scheduler_module = importlib.import_module("src.query_scheduling.scheduler")

        now = dt.datetime(2026, 1, 1, 12, 0, 0)
        db_path = tmp_path / "lease.sqlite"
        make_single_claim_db(db_path, now)
        first = sqlite3.connect(db_path)
        first.row_factory = sqlite3.Row
        second = sqlite3.connect(db_path)
        second.row_factory = sqlite3.Row

        first_scheduler = scheduler_module.QueryScheduler(query_engine=first)
        second_scheduler = scheduler_module.QueryScheduler(query_engine=second)

        first_selected, first_camo = first_scheduler.get_and_lock_query(
            "DE", {"human_user_id": 42, "pod_id": 3}, now=now, thread_id=101
        )
        second_selected, second_camo = second_scheduler.get_and_lock_query(
            "DE", {"human_user_id": 43, "pod_id": 3}, now=now, thread_id=202
        )

        row = first.execute(
            "SELECT human_user_id, locked_at, locked_by_thread FROM query_schedule WHERE id = 11"
        ).fetchone()
        second_row = first.execute(
            "SELECT human_user_id, locked_at, locked_by_thread FROM query_schedule WHERE id = 12"
        ).fetchone()
        assert first_camo is False
        assert first_selected["id"] == 11
        assert second_camo is False
        assert second_selected["id"] == 12
        assert tuple(row) == (42, now.isoformat(timespec="seconds"), 101)
        assert tuple(second_row) == (43, now.isoformat(timespec="seconds"), 202)

    def test_scheduler_records_optional_lock_events(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Optional query_lock_events rows capture claims, reclaims, and unlocks."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        monkeypatch.delenv("GSQT_QUERY_DSN", raising=False)
        clear_src_modules()
        scheduler_module = importlib.import_module("src.query_scheduling.scheduler")

        now = dt.datetime(2026, 1, 1, 12, 0, 0)
        connection = make_query_db(now, include_events=True)
        scheduler = scheduler_module.QueryScheduler(query_engine=connection)

        selected, camo = scheduler.get_and_lock_query(
            "DE", {"human_user_id": 42, "pod_id": 3}, now=now, thread_id=15
        )
        scheduler.unlock_query(selected["id"])
        connection.execute("UPDATE query_schedule SET priority = 120 WHERE id = 8")
        connection.commit()
        reclaimed, reclaim_camo = scheduler.get_and_lock_query(
            "DE", {"human_user_id": 44, "pod_id": 3}, now=now, thread_id=16
        )

        events = connection.execute(
            """
            SELECT query_schedule_id, action, human_user_id, thread_id,
                   event_time, previous_human_user_id, previous_locked_at
            FROM query_lock_events
            ORDER BY id
            """
        ).fetchall()

        assert camo is False
        assert selected["id"] == 7
        assert reclaim_camo is False
        assert reclaimed["id"] == 8
        assert [row["action"] for row in events] == ["claim", "unlock", "reclaim"]
        assert tuple(events[0]) == (
            7,
            "claim",
            42,
            15,
            now.isoformat(timespec="seconds"),
            None,
            None,
        )
        assert events[1]["query_schedule_id"] == 7
        assert events[1]["action"] == "unlock"
        assert tuple(events[2]) == (
            8,
            "reclaim",
            44,
            16,
            now.isoformat(timespec="seconds"),
            88,
            (now - dt.timedelta(minutes=30)).isoformat(timespec="seconds"),
        )

    def test_scheduler_thread_id_is_optional_and_empty_result_returns_camo(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The optional thread id and no-match return contract both work."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        monkeypatch.delenv("GSQT_QUERY_DSN", raising=False)
        clear_src_modules()
        scheduler_module = importlib.import_module("src.query_scheduling.scheduler")

        now = dt.datetime(2026, 1, 1, 12, 0, 0)
        connection = make_query_db(now)
        scheduler = scheduler_module.QueryScheduler(query_engine=connection)

        selected, camo = scheduler.get_and_lock_query(
            "FR", {"human_user_id": 42, "pod_id": 3}, now=now
        )
        assert camo is False
        assert selected["id"] == 3
        locked_at, locked_by_thread = connection.execute(
            "SELECT locked_at, locked_by_thread FROM query_schedule WHERE id = 3"
        ).fetchone()
        assert locked_at == now.isoformat(timespec="seconds")
        assert locked_by_thread is None

        missing, missing_camo = scheduler.get_and_lock_query(
            "ES", {"human_user_id": 42, "pod_id": 3}, now=now
        )
        assert missing is None
        assert missing_camo is True

    def test_services_use_injected_connections_for_steps_and_unlocks(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Step loading and unlock operations use the injected query connection."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        monkeypatch.delenv("GSQT_QUERY_DSN", raising=False)
        clear_src_modules()

        now = dt.datetime(2026, 1, 1, 12, 0, 0)
        connection = make_query_db(now)
        generator_module = importlib.import_module("src.steps.generator")
        scheduler_module = importlib.import_module("src.query_scheduling.scheduler")
        user_module = importlib.import_module("src.user_service")

        steps = generator_module.StepBuilder(query_engine=connection).build_query_steps({"id": 7})
        assert [step["type"] for step in steps] == ["google_search", "click_result"]
        assert [step["step_number"] for step in steps] == [1, 2]
        assert set(steps[0]) == {"step_number", "type", "value", "done", "url", "title"}
        assert steps[0]["value"] == "best pasta berlin"
        assert steps[0]["done"] is None
        assert steps[0]["url"] is None
        assert steps[0]["title"] is None

        legacy_steps = generator_module.StepBuilder(
            query_engine=make_legacy_step_db_without_position()
        ).build_query_steps({"id": 900})
        assert [step["type"] for step in legacy_steps] == ["google_search", "click_result"]
        assert [step["step_number"] for step in legacy_steps] == [1, 2]

        nullable_position_steps = generator_module.StepBuilder(
            query_engine=make_nullable_position_step_db()
        ).build_query_steps({"id": 901})
        assert [step["type"] for step in nullable_position_steps] == [
            "google_search",
            "click_result",
            "archive_result",
        ]
        assert [step["step_number"] for step in nullable_position_steps] == [1, 2, 3]

        scheduler_module.QueryScheduler(query_engine=connection).unlock_query(2)
        user_module.UserService(query_engine=connection).unlock_user(42)

        assert tuple(
            connection.execute(
                "SELECT human_user_id, locked_at, locked_by_thread FROM query_schedule WHERE id = 2"
            ).fetchone()
        ) == (None, None, None)
        assert connection.execute(
            "SELECT last_locked FROM human_users WHERE id = 42"
        ).fetchone()[0] is None

    def test_node_service_uses_injected_node_database(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """NodeService returns online nodes and user pool rows from an injected DB."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        monkeypatch.delenv("GSQT_NODE_DSN", raising=False)
        clear_src_modules()
        node_module = importlib.import_module("src.node_service")

        online_nodes, user_pool = node_module.NodeService(
            node_engine=make_node_db()
        ).get_online_nodes_and_user_pool()

        assert online_nodes == [{"uuid": "node-a", "currently_online": "TRUE"}]
        assert user_pool == [
            {
                "human_user_id": 42,
                "uuid": "node-a",
                "currently_online": "TRUE",
                "node_country": "DE",
            },
            {
                "human_user_id": 44,
                "uuid": "node-a",
                "currently_online": "TRUE",
                "node_country": "DE",
            },
        ]

    def test_services_fall_back_to_lazy_accessors_when_not_injected(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Services without injected connections use the configured lazy accessors."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        now = dt.datetime(2026, 1, 1, 12, 0, 0)
        query_path = tmp_path / "query.sqlite"
        node_path = tmp_path / "node.sqlite"
        make_query_db(now, query_path).close()
        make_node_db(node_path).close()
        monkeypatch.setenv("GSQT_QUERY_DSN", str(query_path))
        monkeypatch.setenv("GSQT_NODE_DSN", str(node_path))
        clear_src_modules()

        generator_module = importlib.import_module("src.steps.generator")
        node_module = importlib.import_module("src.node_service")
        scheduler_module = importlib.import_module("src.query_scheduling.scheduler")
        user_module = importlib.import_module("src.user_service")

        scheduler = scheduler_module.QueryScheduler()
        selected, camo = scheduler.get_and_lock_query(
            "DE", {"human_user_id": 42, "pod_id": 3}, now=now, thread_id=14
        )
        steps = generator_module.StepBuilder().build_query_steps(selected)
        scheduler.unlock_query(selected["id"])
        user_module.UserService().unlock_user(42)
        online_nodes, user_pool = node_module.NodeService().get_online_nodes_and_user_pool()

        assert camo is False
        assert selected["id"] == 7
        assert [step["type"] for step in steps] == ["google_search", "click_result"]
        assert online_nodes == [{"uuid": "node-a", "currently_online": "TRUE"}]
        assert [row["human_user_id"] for row in user_pool] == [42, 44]
