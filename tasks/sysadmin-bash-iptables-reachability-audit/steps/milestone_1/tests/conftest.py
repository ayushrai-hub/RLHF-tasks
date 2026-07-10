import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from helpers import assert_protected_files_unchanged  # noqa: E402


def pytest_collection_modifyitems(config, items):
    assert_protected_files_unchanged()
