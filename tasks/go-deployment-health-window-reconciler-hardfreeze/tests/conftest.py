"""Small local CTRF writer for Harbor-compatible pytest runs."""

from __future__ import annotations

import json
import time
from pathlib import Path

_RESULTS = []
_STARTED_AT = 0.0


def pytest_addoption(parser):
    """Register the --ctrf option when no external CTRF plugin is installed."""
    parser.addoption("--ctrf", action="store", default=None, help="Write a CTRF JSON report")


def pytest_configure(config):
    """Initialize per-run result storage."""
    global _RESULTS
    global _STARTED_AT
    _RESULTS = []
    _STARTED_AT = time.time()


def pytest_runtest_logreport(report):
    """Collect one result per test call phase."""
    if report.when != "call":
        return
    _RESULTS.append(
        {
            "name": report.nodeid,
            "status": "passed" if report.passed else "failed",
            "duration": report.duration,
            "message": str(report.longrepr) if report.failed else "",
        }
    )


def pytest_sessionfinish(session, exitstatus):
    """Write a minimal CTRF report to the path requested by --ctrf."""
    output_path = session.config.getoption("--ctrf")
    if not output_path:
        return
    passed = sum(1 for result in _RESULTS if result["status"] == "passed")
    failed = sum(1 for result in _RESULTS if result["status"] == "failed")
    report = {
        "results": {
            "tool": {"name": "pytest"},
            "summary": {
                "tests": len(_RESULTS),
                "passed": passed,
                "failed": failed,
                "pending": 0,
                "skipped": 0,
                "other": 0,
                "start": _STARTED_AT,
                "stop": time.time(),
            },
            "tests": _RESULTS,
        }
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
