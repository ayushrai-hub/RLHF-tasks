"""Minimal CTRF writer for offline pytest environments."""
import json
import time
from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption("--ctrf", action="store", default=None, help="write a CTRF JSON report")


def pytest_configure(config):
    config._ctrf_start_time = time.time()
    config._ctrf_results = []


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call":
        return
    if report.passed:
        status = "passed"
    elif report.failed:
        status = "failed"
    else:
        status = "skipped"
    message = str(report.longrepr) if report.failed else ""
    item.config._ctrf_results.append(
        {
            "name": item.name,
            "status": status,
            "duration": int(report.duration * 1000),
            "message": message,
        }
    )


def pytest_sessionfinish(session, exitstatus):
    ctrf_path = session.config.getoption("--ctrf")
    if not ctrf_path:
        return
    results = getattr(session.config, "_ctrf_results", [])
    summary = {
        "tests": len(results),
        "passed": sum(1 for result in results if result["status"] == "passed"),
        "failed": sum(1 for result in results if result["status"] == "failed"),
        "skipped": sum(1 for result in results if result["status"] == "skipped"),
        "pending": 0,
        "other": 0,
        "start": int(getattr(session.config, "_ctrf_start_time", time.time()) * 1000),
        "stop": int(time.time() * 1000),
    }
    report = {"results": {"tool": {"name": "pytest"}, "summary": summary, "tests": results}}
    path = Path(ctrf_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
