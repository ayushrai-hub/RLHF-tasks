"""Tests for milestone 1 — depfile generation matches per-target include closure."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reference_depfix import (
    compute_depfile_digest,
    compute_header_closure,
    parse_depfile,
    public_include_checksum,
)

APP = Path("/app")
BUILD = APP / "build"
DEPS = BUILD / "deps"
STALE = BUILD / "deps-stale"
TARGETS = ("depfix_hash", "depfix_core", "depfix_util", "depfix_app")


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(APP), capture_output=True, text=True, check=False)


def _refresh_depfiles() -> None:
    """Force POST_BUILD dep normalization to run for every depfix target."""
    for target in TARGETS:
        _run(["ninja", "-C", str(BUILD), "-t", "clean", target])
    build = _run(["cmake", "--build", str(BUILD)])
    assert build.returncode == 0, build.stderr


def _dep_data_lines(target: str) -> list[str]:
    data, _footer = parse_depfile(DEPS / f"{target}.dep")
    return data


class TestMilestone1:
    """Depfiles must land in build/deps with live sorted per-target header closure."""

    def test_public_include_tree_checksum(self) -> None:
        """Public header tree must match the pinned verifier checksum."""
        assert public_include_checksum() == (
            "891a187710899171b5713f8c49f8e1a7a9911a2957630b8bbea0a0d0c4dcbbc8"
        )

    def test_cmake_ninja_configure_build(self) -> None:
        """Project must configure with Ninja and build successfully."""
        cfg = _run(["cmake", "-G", "Ninja", "-S", str(APP), "-B", str(BUILD)])
        assert cfg.returncode == 0, cfg.stderr
        build = _run(["ninja", "-C", str(BUILD)])
        assert build.returncode == 0, build.stderr
        _refresh_depfiles()

    def test_depfiles_live_under_build_deps(self) -> None:
        """Normalized manifests must be written to /app/build/deps, not deps-stale."""
        for target in TARGETS:
            assert (DEPS / f"{target}.dep").is_file(), target
        assert not STALE.exists() or not any(STALE.glob("*.dep")), "stale deps dir must be unused"

    def test_stale_overlay_does_not_clobber_live_depfiles(self) -> None:
        """PRE_BUILD stale overlay must not restore old/ paths into live dep manifests."""
        for target in TARGETS:
            lines = _dep_data_lines(target)
            assert not any("include/depfix/old/" in ln for ln in lines), (target, lines)

    def test_build_ninja_excludes_stale_publish_steps(self) -> None:
        """Generated Ninja rules must not invoke stale overlay or publish scripts."""
        ninja_file = BUILD / "build.ninja"
        assert ninja_file.is_file(), "missing build.ninja"
        body = ninja_file.read_text(encoding="utf-8")
        assert "depfix_overlay.cmake" not in body, "PRE_BUILD stale overlay still wired"
        assert "depfix_publish.cmake" not in body, "POST_BUILD stale publish still wired"

    def test_depfile_lines_sorted_lexicographically(self) -> None:
        """Data lines in each depfile must be ascending lex sort per contract."""
        for target in TARGETS:
            lines = _dep_data_lines(target)
            assert lines == sorted(lines), (target, lines)

    def test_depfile_footer_digest_matches_data(self) -> None:
        """Footer line count and digest must match sorted data lines per contract."""
        for target in TARGETS:
            data, footer = parse_depfile(DEPS / f"{target}.dep")
            assert footer.get("lines") == str(len(data)), (target, footer, data)
            assert footer.get("digest") == compute_depfile_digest(data), (target, footer)

    def test_hash_depfile_matches_include_closure(self) -> None:
        """depfix_hash.dep must list exactly the headers reachable from hash_mix.cpp."""
        assert _dep_data_lines("depfix_hash") == compute_header_closure("depfix_hash")

    def test_hash_depfile_excludes_foreign_headers(self) -> None:
        """depfix_hash closure must not pull headers from util/core translation units."""
        hash_lines = set(_dep_data_lines("depfix_hash"))
        foreign = {
            "include/depfix/util.hpp",
            "include/depfix/config.hpp",
            "include/depfix/detail/compile_fence.hpp",
        }
        assert foreign.isdisjoint(hash_lines), (hash_lines, foreign)

    def test_core_depfile_matches_include_closure(self) -> None:
        """depfix_core.dep must list exactly the headers reachable from core.cpp."""
        assert _dep_data_lines("depfix_core") == compute_header_closure("depfix_core")

    def test_util_depfile_matches_include_closure(self) -> None:
        """depfix_util.dep must list exactly the headers reachable from util.cpp."""
        assert _dep_data_lines("depfix_util") == compute_header_closure("depfix_util")

    def test_app_depfile_matches_include_closure(self) -> None:
        """depfix_app.dep must list exactly the headers reachable from main.cpp."""
        assert _dep_data_lines("depfix_app") == compute_header_closure("depfix_app")

    def test_core_closure_includes_generated_revision(self) -> None:
        """core.cpp closure must include generated/revision.hpp via version.hpp."""
        core = compute_header_closure("depfix_core")
        assert "include/depfix/generated/revision.hpp" in core

    def test_core_closure_includes_compile_fence(self) -> None:
        """core.cpp closure must include detail/compile_fence.hpp from core.cpp."""
        core = compute_header_closure("depfix_core")
        assert "include/depfix/detail/compile_fence.hpp" in core
