import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from helpers import (  # noqa: E402
    DB_PATH,
    TRACE_REPORT_PATH,
    assert_protected_files_unchanged,
)


def pytest_collection_modifyitems(config, items):
    assert_protected_files_unchanged()


@pytest.fixture(scope="session", autouse=True)
def artifacts_exist():
    missing = [str(p) for p in (DB_PATH, TRACE_REPORT_PATH)
               if not p.exists() or p.stat().st_size == 0]
    if missing:
        pytest.fail(f"pipeline artifacts missing or empty: {missing}")
