import json
import time
from pathlib import Path

_RESULTS = []
_START = {"t": None}


def pytest_addoption(parser):
    parser.addoption(
        "--ctrf",
        action="store",
        default=None,
        metavar="PATH",
        help="Write a CTRF (Common Test Report Format) JSON report to PATH.",
    )


def pytest_sessionstart(session):
    _START["t"] = int(time.time() * 1000)


def pytest_runtest_logreport(report):
    if report.when != "call" and not (report.when == "setup" and report.skipped):
        return
    if report.passed:
        status = "passed"
    elif report.skipped:
        status = "skipped"
    else:
        status = "failed"
    _RESULTS.append(
        {
            "name": report.nodeid,
            "status": status,
            "duration": int(report.duration * 1000),
            "message": str(report.longrepr) if report.failed else "",
        }
    )


def pytest_sessionfinish(session, exitstatus):
    path = session.config.getoption("--ctrf")
    if not path:
        return
    passed = sum(1 for r in _RESULTS if r["status"] == "passed")
    failed = sum(1 for r in _RESULTS if r["status"] == "failed")
    skipped = sum(1 for r in _RESULTS if r["status"] == "skipped")
    report = {
        "results": {
            "tool": {"name": "pytest"},
            "summary": {
                "tests": len(_RESULTS),
                "passed": passed,
                "failed": failed,
                "pending": 0,
                "skipped": skipped,
                "other": 0,
                "start": _START["t"] or 0,
                "stop": int(time.time() * 1000),
            },
            "tests": _RESULTS,
        }
    }
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
