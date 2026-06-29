"""Node lookup helpers."""

from __future__ import annotations

from src.config.database import get_node_engine


class NodeService:
    """Node service with lazy database access."""

    @staticmethod
    def get_online_nodes_and_user_pool() -> tuple[list[dict], list[dict]]:
        node_engine = get_node_engine()
        rows = node_engine.execute(
            """
            SELECT nhu.human_user_id, n.uuid, n.currently_online, n.country AS node_country
            FROM nodes_to_human_users AS nhu
            INNER JOIN nodes AS n ON nhu.node_uuid = n.uuid
            WHERE n.currently_online = 'TRUE'
            ORDER BY n.uuid
            """
        ).fetchall()

        if not rows:
            return [], []

        user_pool = [dict(row) for row in rows]
        online_nodes = [
            {"uuid": row["uuid"], "currently_online": row["currently_online"]}
            for row in rows
        ]
        return online_nodes, user_pool
