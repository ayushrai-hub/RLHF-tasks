"""Pytest fixtures for r8 replay grading.

Session helpers invoke replay CLIs under /app/environment/tools.
"""

from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "/app/docs")

from r8_session import R8ReplaySession, cargo_rebuild


@pytest.fixture(scope="session", autouse=True)
def _rebuild_r8_binaries() -> None:
    cargo_rebuild()


@pytest.fixture
def session() -> R8ReplaySession:
    return R8ReplaySession()
