import json
import time
from pathlib import Path


def pytest_addoption(parser):
    parser.addoption("--ctrf", action="store", default=None, help="write a minimal CTRF report")


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    out = config.getoption("--ctrf")
    if not out:
        return
    tests = []
    for outcome in ("passed", "failed", "skipped"):
        for rep in terminalreporter.stats.get(outcome, []):
            tests.append({
                "name": rep.nodeid,
                "status": "passed" if outcome == "passed" else ("failed" if outcome == "failed" else "skipped"),
                "duration": getattr(rep, "duration", 0.0),
            })
    report = {
        "results": {
            "tool": {"name": "pytest"},
            "summary": {
                "tests": len(tests),
                "passed": sum(1 for t in tests if t["status"] == "passed"),
                "failed": sum(1 for t in tests if t["status"] == "failed"),
                "skipped": sum(1 for t in tests if t["status"] == "skipped"),
                "start": int(time.time() * 1000),
                "stop": int(time.time() * 1000),
            },
            "tests": tests,
        }
    }
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
