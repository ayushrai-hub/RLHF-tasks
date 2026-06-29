"""Tests for milestone 2 — header sync and compiler deps drive incremental rebuilds."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

APP = Path("/app")
BUILD = APP / "build"
CONFIG = APP / "include" / "depfix" / "config.hpp"
VERSION = APP / "include" / "depfix" / "version.hpp"
LEGACY = APP / "include" / "depfix" / "legacy_alias.hpp"
UTIL_OBJ = BUILD / "CMakeFiles" / "depfix_util.dir" / "src" / "util.cpp.o"
CORE_OBJ = BUILD / "CMakeFiles" / "depfix_core.dir" / "src" / "core.cpp.o"
APP_BIN = BUILD / "depfix_app"
STAMP = BUILD / "depfix_header.stamp"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(APP), capture_output=True, text=True, check=False)


def _touch_append(path: Path) -> None:
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")


class TestMilestone2:
    """Header sync stamp and -MP must rebuild util/core objects on header edits."""

    def test_config_touch_rebuilds_util_object(self) -> None:
        """Touching config.hpp must rebuild util.cpp.o via ninja."""
        assert UTIL_OBJ.is_file(), f"missing object file {UTIL_OBJ}"
        before = UTIL_OBJ.stat().st_mtime_ns
        time.sleep(0.05)
        _touch_append(CONFIG)
        ninja = _run(["ninja", "-C", str(BUILD)])
        assert ninja.returncode == 0, ninja.stderr
        assert UTIL_OBJ.stat().st_mtime_ns > before

    def test_config_touch_rebuilds_linked_app(self) -> None:
        """Touching config.hpp must relink depfix_app after util rebuild."""
        assert APP_BIN.is_file(), f"missing binary {APP_BIN}"
        before = APP_BIN.stat().st_mtime_ns
        time.sleep(0.05)
        _touch_append(CONFIG)
        ninja = _run(["ninja", "-C", str(BUILD)])
        assert ninja.returncode == 0, ninja.stderr
        assert APP_BIN.stat().st_mtime_ns > before

    def test_version_touch_rebuilds_core_object(self) -> None:
        """Touching version.hpp must rebuild core.cpp.o via ninja."""
        assert CORE_OBJ.is_file(), f"missing object file {CORE_OBJ}"
        before = CORE_OBJ.stat().st_mtime_ns
        time.sleep(0.05)
        _touch_append(VERSION)
        ninja = _run(["ninja", "-C", str(BUILD)])
        assert ninja.returncode == 0, ninja.stderr
        assert CORE_OBJ.stat().st_mtime_ns > before

    def test_legacy_alias_touch_rebuilds_util_object(self) -> None:
        """Touching legacy_alias.hpp must rebuild util.cpp.o via ninja."""
        assert UTIL_OBJ.is_file(), f"missing object file {UTIL_OBJ}"
        before = UTIL_OBJ.stat().st_mtime_ns
        time.sleep(0.05)
        _touch_append(LEGACY)
        ninja = _run(["ninja", "-C", str(BUILD)])
        assert ninja.returncode == 0, ninja.stderr
        assert UTIL_OBJ.stat().st_mtime_ns > before

    def test_app_binary_still_runs(self) -> None:
        """Linked demo binary must still print depfix_app=31."""
        build = _run(["ninja", "-C", str(BUILD)])
        assert build.returncode == 0, build.stderr
        proc = _run([str(APP_BIN)])
        assert proc.returncode == 0, proc.stderr + proc.stdout
        assert "depfix_app=31" in proc.stdout

    def test_header_sync_stamp_target_exists(self) -> None:
        """Ninja must expose depfix_header_sync phony target."""
        targets = _run(["ninja", "-C", str(BUILD), "-t", "targets", "all"])
        assert targets.returncode == 0, targets.stderr
        assert "depfix_header_sync:" in targets.stdout

    def test_stamp_rule_tracks_config_and_version(self) -> None:
        """depfix_header.stamp inputs must include config.hpp and version.hpp."""
        query = _run(["ninja", "-C", str(BUILD), "-t", "query", str(STAMP)])
        assert query.returncode == 0, query.stderr
        body = query.stdout
        assert "config.hpp" in body, body
        assert "version.hpp" in body, body

    def test_util_target_depends_on_header_sync(self) -> None:
        """libdepfix_util.a must list depfix_header_sync in Ninja's dependency graph."""
        query = _run(["ninja", "-C", str(BUILD), "-t", "query", "libdepfix_util.a"])
        assert query.returncode == 0, query.stderr
        assert "depfix_header_sync" in query.stdout, query.stdout

    def test_core_target_depends_on_header_sync(self) -> None:
        """libdepfix_core.a must list depfix_header_sync in Ninja's dependency graph."""
        query = _run(["ninja", "-C", str(BUILD), "-t", "query", "libdepfix_core.a"])
        assert query.returncode == 0, query.stderr
        assert "depfix_header_sync" in query.stdout, query.stdout

    def test_app_target_depends_on_header_sync(self) -> None:
        """depfix_app must list depfix_header_sync in Ninja's dependency graph."""
        query = _run(["ninja", "-C", str(BUILD), "-t", "query", "depfix_app"])
        assert query.returncode == 0, query.stderr
        assert "depfix_header_sync" in query.stdout, query.stdout

    def test_util_and_app_compile_with_dependency_flags(self) -> None:
        """util.cpp.o and main.cpp.o compile rules must pass -MD and -MP."""
        _run(["ninja", "-C", str(BUILD), "-t", "clean", "depfix_util", "depfix_app"])
        build = _run(["ninja", "-C", str(BUILD), "depfix_util", "depfix_app"])
        assert build.returncode == 0, build.stderr
        for obj in (
            "CMakeFiles/depfix_util.dir/src/util.cpp.o",
            "CMakeFiles/depfix_app.dir/src/main.cpp.o",
        ):
            commands = _run(["ninja", "-C", str(BUILD), "-t", "commands", obj])
            assert commands.returncode == 0, commands.stderr
            assert "-MP" in commands.stdout, commands.stdout
            assert "-MD" in commands.stdout, commands.stdout
