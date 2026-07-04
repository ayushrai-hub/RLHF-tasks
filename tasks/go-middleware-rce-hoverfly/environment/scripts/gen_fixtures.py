from __future__ import annotations
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
VALID_DIR = BASE / "testdata" / "valid"
EXPLOIT_DIR = BASE / "testdata" / "exploits"
REMOTE_DIR = BASE / "testdata" / "remote"

VALID_DIR.mkdir(parents=True, exist_ok=True)
EXPLOIT_DIR.mkdir(parents=True, exist_ok=True)
REMOTE_DIR.mkdir(parents=True, exist_ok=True)

ADMIN_TOKEN = "admin-token"


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def make_request(
    *,
    enable_api: bool,
    token: str,
    validate: bool,
    mode: str,
    binary: str,
    script: str,
    remote_path: str | None,
    payload_id: str,
    payload_body: str,
) -> dict:
    req = {
        "enable_middleware_api": enable_api,
        "auth_token": token,
        "validate": validate,
        "middleware": {
            "mode": mode,
            "binary": binary,
            "script": script,
            "remote_path": remote_path or "",
        },
        "payload": {
            "request_id": payload_id,
            "path": "/api/check",
            "method": "GET",
            "body": payload_body,
        },
    }
    return req


remote_files = {
    "remote_001.json": {"source": "remote", "id": "remote_001", "data": "alpha"},
    "remote_002.json": {"source": "remote", "id": "remote_002", "data": "bravo"},
    "remote_003.json": {"source": "remote", "id": "remote_003", "data": "charlie"},
}

for name, payload in remote_files.items():
    write_json(REMOTE_DIR / name, payload)

remote_001 = "testdata/remote/remote_001.json"
remote_002 = "testdata/remote/remote_002.json"
remote_003 = "testdata/remote/remote_003.json"

valid = [
    make_request(
        enable_api=True,
        token=ADMIN_TOKEN,
        validate=True,
        mode="local",
        binary="mw-runner",
        script="noop",
        remote_path=None,
        payload_id="v001",
        payload_body="ping",
    ),
    make_request(
        enable_api=True,
        token=ADMIN_TOKEN,
        validate=True,
        mode="local",
        binary="mw-runner",
        script="trim",
        remote_path=None,
        payload_id="v002",
        payload_body="pong",
    ),
    make_request(
        enable_api=True,
        token=ADMIN_TOKEN,
        validate=False,
        mode="local",
        binary="mw-runner",
        script="upper",
        remote_path=None,
        payload_id="v003",
        payload_body="ok",
    ),
    make_request(
        enable_api=True,
        token=ADMIN_TOKEN,
        validate=True,
        mode="remote",
        binary="mw-runner",
        script="noop",
        remote_path=remote_001,
        payload_id="v004",
        payload_body="r1",
    ),
    make_request(
        enable_api=True,
        token=ADMIN_TOKEN,
        validate=True,
        mode="remote",
        binary="mw-runner",
        script="lower",
        remote_path=remote_002,
        payload_id="v005",
        payload_body="r2",
    ),
    make_request(
        enable_api=True,
        token=ADMIN_TOKEN,
        validate=True,
        mode="local",
        binary="mw-runner",
        script="noop-1",
        remote_path=None,
        payload_id="v006",
        payload_body="edge",
    ),
    make_request(
        enable_api=True,
        token=ADMIN_TOKEN,
        validate=True,
        mode="local",
        binary="mw-runner",
        script="noop.1",
        remote_path=None,
        payload_id="v007",
        payload_body="edge2",
    ),
    make_request(
        enable_api=True,
        token=ADMIN_TOKEN,
        validate=True,
        mode="remote",
        binary="mw-runner",
        script="noop_2",
        remote_path=remote_003,
        payload_id="v008",
        payload_body="edge3",
    ),
]

for idx, payload in enumerate(valid, start=1):
    write_json(VALID_DIR / f"valid_{idx:03d}.json", payload)

exploit_binary = make_request(
    enable_api=True,
    token=ADMIN_TOKEN,
    validate=True,
    mode="local",
    binary="/bin/sh",
    script="-c echo exploit_binary",
    remote_path=None,
    payload_id="e001",
    payload_body="x",
)

exploit_local = make_request(
    enable_api=True,
    token=ADMIN_TOKEN,
    validate=True,
    mode="local",
    binary="mw-runner",
    script="ok; echo exploit_local",
    remote_path=None,
    payload_id="e002",
    payload_body="y",
)

exploit_remote = make_request(
    enable_api=True,
    token=ADMIN_TOKEN,
    validate=True,
    mode="remote",
    binary="mw-runner",
    script="noop",
    remote_path=remote_001 + "; echo exploit_remote",
    payload_id="e003",
    payload_body="z",
)

exploit_api = make_request(
    enable_api=False,
    token="nope",
    validate=True,
    mode="local",
    binary="mw-runner",
    script="noop",
    remote_path=None,
    payload_id="e004",
    payload_body="w",
)

exploit_token = make_request(
    enable_api=True,
    token=ADMIN_TOKEN.upper(),
    validate=True,
    mode="local",
    binary="mw-runner",
    script="noop",
    remote_path=None,
    payload_id="e005",
    payload_body="t",
)

write_json(EXPLOIT_DIR / "exploit_binary.json", exploit_binary)
write_json(EXPLOIT_DIR / "exploit_local.json", exploit_local)
write_json(EXPLOIT_DIR / "exploit_remote.json", exploit_remote)
write_json(EXPLOIT_DIR / "exploit_api.json", exploit_api)
write_json(EXPLOIT_DIR / "exploit_token.json", exploit_token)
