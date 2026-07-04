"""Pytest fixtures for the routenet sampler verifier.

The session fixture brings up the local PostgreSQL cluster (if it is not
already running) and exposes a psycopg2 connection. It also recomputes the
ground-truth edge sets and train-subgraph distance map from the live database,
so individual tests do not have to re-query.
"""

from __future__ import annotations

import json
import subprocess
import time
from collections import deque
from pathlib import Path

import psycopg2
import pytest


DB_CONFIG_PATH = "/app/config/db.json"


def _load_db_config() -> dict:
    return json.loads(Path(DB_CONFIG_PATH).read_text())


def _try_connect(cfg: dict):
    return psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        dbname=cfg["database"],
        connect_timeout=2,
    )


def _ensure_postgres_up(cfg: dict) -> None:
    try:
        subprocess.run(
            ["bash", "/app/scripts/start-system.sh"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "postgres cluster failed to start via /app/scripts/start-system.sh "
            f"(exit {exc.returncode})\nstdout:\n{exc.stdout}\nstderr:\n{exc.stderr}"
        ) from exc

    deadline = time.time() + 90.0
    last_err = None
    while time.time() < deadline:
        try:
            conn = _try_connect(cfg)
            conn.close()
            return
        except Exception as exc:
            last_err = exc
        time.sleep(1.0)

    raise RuntimeError(
        f"postgres did not become reachable within 90s after start-system.sh: {last_err!r}"
    )


@pytest.fixture(scope="session")
def db_cfg() -> dict:
    return _load_db_config()


@pytest.fixture(scope="session")
def db_conn(db_cfg):
    _ensure_postgres_up(db_cfg)
    conn = psycopg2.connect(
        host=db_cfg["host"],
        port=db_cfg["port"],
        user=db_cfg["user"],
        password=db_cfg["password"],
        dbname=db_cfg["database"],
    )
    yield conn
    conn.close()


def _canon(u: int, v: int) -> tuple[int, int]:
    return (u, v) if u < v else (v, u)


@pytest.fixture(scope="session")
def graph_facts(db_conn):
    """Pull node ids and the three edge splits from Postgres."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT id FROM nodes ORDER BY id")
        node_ids = [row[0] for row in cur.fetchall()]

        cur.execute("SELECT u, v, split FROM edges")
        rows = cur.fetchall()

    train_edges = set()
    val_edges = set()
    test_edges = set()
    all_edges = set()
    for u, v, split in rows:
        pair = _canon(int(u), int(v))
        all_edges.add(pair)
        if split == "train":
            train_edges.add(pair)
        elif split == "val":
            val_edges.add(pair)
        elif split == "test":
            test_edges.add(pair)

    adj: dict[int, set[int]] = {nid: set() for nid in node_ids}
    for u, v in train_edges:
        adj[u].add(v)
        adj[v].add(u)

    def shortest(src: int) -> dict[int, int]:
        dist = {src: 0}
        q = deque([src])
        while q:
            x = q.popleft()
            for y in adj.get(x, ()):
                if y not in dist:
                    dist[y] = dist[x] + 1
                    q.append(y)
        return dist

    distances = {nid: shortest(nid) for nid in node_ids}

    return {
        "node_ids": set(node_ids),
        "train_edges": train_edges,
        "val_edges": val_edges,
        "test_edges": test_edges,
        "all_edges": all_edges,
        "distances": distances,
    }


@pytest.fixture(scope="session")
def output_dir(tmp_path_factory) -> Path:
    """Working directory that holds sampler/audit outputs produced by tests.

    We deliberately use a tmp dir rather than the shared /app/output/ so that
    each invocation in the test session is hermetic - the agent's run of the
    CLI writes wherever it wants, but the verifier-driven invocations don't
    have to fight for the same paths.
    """
    return tmp_path_factory.mktemp("sampler-out")
