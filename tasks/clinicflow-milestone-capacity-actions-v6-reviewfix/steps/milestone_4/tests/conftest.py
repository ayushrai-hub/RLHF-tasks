from __future__ import annotations

import json
from pathlib import Path


def pytest_addoption(parser):
    parser.addoption("--ctrf", action="store", default=None)


def pytest_sessionfinish(session, exitstatus):
    target = session.config.getoption("--ctrf")
    if target:
        path = Path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "results": {
                "tool": {"name": "pytest"},
                "summary": {"tests": session.testscollected, "failed": int(exitstatus != 0)},
            }
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
