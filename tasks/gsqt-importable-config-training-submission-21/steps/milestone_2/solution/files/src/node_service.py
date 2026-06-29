"""Node lookup helpers."""

from __future__ import annotations

import sqlite3

from src.config.database import get_node_engine


class NodeService:
    """Node service with injectable database access."""

    def __init__(self, node_engine: sqlite3.Connection | None = None):
        self._node_engine = node_engine

    @property
    def node_engine(self) -> sqlite3.Connection:
        return self._node_engine or get_node_engine()

    def get_online_nodes_and_user_pool(self) -> tuple[list[dict], list[dict]]:
        rows = self.node_engine.execute(
            """
            SELECT nhu.human_user_id, n.uuid, n.currently_online, n.country AS node_country
            FROM nodes_to_human_users AS nhu
            INNER JOIN nodes AS n ON nhu.node_uuid = n.uuid
            WHERE n.currently_online = 'TRUE'
            ORDER BY n.uuid, nhu.human_user_id
            """
        ).fetchall()

        if not rows:
            return [], []

        user_pool = []
        online_nodes = []
        seen_pool = set()
        seen_nodes = set()
        for row in rows:
            node_key = row["uuid"]
            if node_key not in seen_nodes:
                seen_nodes.add(node_key)
                online_nodes.append({"uuid": row["uuid"], "currently_online": row["currently_online"]})

            pool_key = (row["uuid"], row["human_user_id"])
            if pool_key not in seen_pool:
                seen_pool.add(pool_key)
                user_pool.append(dict(row))
        return online_nodes, user_pool
