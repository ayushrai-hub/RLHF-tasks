"""Mock iptables snapshot API.

Serves /health and /api/iptables-snapshot. The snapshot endpoint returns a
pre-parsed iptables-save state for table=filter, with chain metadata
(name, kind, default_policy for builtins) and per-rule records (chain,
position, matcher_text, target, target_args, packet_count, byte_count).
"""
from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify

DATA_DIR = Path(__file__).parent / "data"

app = Flask(__name__)


@app.get("/health")
def health() -> tuple[dict, int]:
    return {"status": "ok"}, 200


@app.get("/api/iptables-snapshot")
def iptables_snapshot():
    with (DATA_DIR / "iptables_snapshot.json").open() as f:
        return jsonify(json.load(f))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080)
