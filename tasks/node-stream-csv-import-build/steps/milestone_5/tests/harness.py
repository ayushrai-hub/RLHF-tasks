"""Shared verifier harness for the catalog-feed importer task.

Generates fresh binary feeds per run (Pattern H: random seed + nonce so nothing
is hardcodable), runs the agent importer, and exposes the behavioural anti-cheat
helpers (probe moved aside during the graded run, plus a side-channel source scan
of the launched deliverable only).
"""
import os
import re
import secrets
import subprocess
import contextlib

import feedgen

PROBE = "/app/ref/catalog-probe"
IMPORT = "/app/import.js"


def psql(query: str, timeout: int = 60) -> tuple[int, str]:
    r = subprocess.run(
        ["sudo", "-u", "postgres", "psql", "-p", "5433", "-d", "app",
         "-tA", "-c", query],
        capture_output=True, text=True, timeout=timeout,
    )
    return r.returncode, r.stdout.strip()


def rand_seed() -> int:
    return 1 + secrets.randbelow(1000)


def write_catalog(path: str, n: int, version: int, seed: int) -> list:
    recs = feedgen.gen_products(n, seed)
    feedgen.write_feed(path, recs, version)
    return recs


def write_changelog(path: str, nids: int, seed: int) -> list:
    recs = feedgen.gen_changelog(nids, seed)
    feedgen.write_feed(path, recs, 4)
    return recs


def write_feed(path: str, records: list, version: int) -> None:
    feedgen.write_feed(path, records, version)


@contextlib.contextmanager
def probe_stashed():
    """Move the reference probe aside for the duration of the graded run, so an
    importer that shells out to it at runtime fails behaviourally."""
    stash = "/app/ref/.stash-probe"
    moved = False
    if os.path.exists(PROBE):
        os.rename(PROBE, stash)
        moved = True
    try:
        yield
    finally:
        if moved:
            os.rename(stash, PROBE)


def run_import(args, timeout=200, heap_mb=None):
    env = dict(os.environ)
    if heap_mb is not None:
        env["NODE_OPTIONS"] = f"--max-old-space-size={heap_mb}"
    with probe_stashed():
        return subprocess.run(
            ["node", IMPORT, *args],
            capture_output=True, text=True, timeout=timeout, env=env,
        )


def _strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.DOTALL)
    src = re.sub(r"//[^\n]*", " ", src)
    return src


def assert_no_side_channel():
    """The launched deliverable must decode feeds itself, not shell out to the
    reference probe or a separate interpreter. Scans only the importer sources
    that actually run (comments stripped), not arbitrary scratch files."""
    banned = ["child_process", "execSync", "execFileSync", "spawnSync", "spawn(",
              "catalog-probe", "/app/ref", "wc -l", "require('python", '"python"']
    targets = [IMPORT]
    lib = "/app/lib"
    if os.path.isdir(lib):
        for f in os.listdir(lib):
            if f.endswith(".js"):
                targets.append(os.path.join(lib, f))
    for t in targets:
        if not os.path.exists(t):
            continue
        code = _strip_comments(open(t).read())
        for b in banned:
            assert b not in code, (
                f"{t} references {b!r}; the importer must decode the feed itself, "
                f"not shell out to the reference probe or another process"
            )
