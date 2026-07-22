#!/usr/bin/env python3
"""Preflight checks for Terminus review tooling (Docker, harbor, Python deps)."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
REQUIREMENTS = REPO_ROOT / "requirements.txt"


def check(label: str, ok: bool, detail: str = "") -> bool:
    icon = "✓" if ok else "✗"
    line = f"{icon} {label}"
    if detail:
        line += f" — {detail}"
    print(line)
    return ok


def docker_ok() -> tuple[bool, str]:
    if not shutil.which("docker"):
        return False, "docker not on PATH"
    try:
        proc = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=15)
        if proc.returncode == 0:
            ver = ""
            for line in (proc.stdout or "").splitlines():
                if "Server Version" in line:
                    ver = line.split(":", 1)[-1].strip()
                    break
            return True, ver or "daemon reachable"
        return False, (proc.stderr or proc.stdout or "docker info failed").strip().splitlines()[-1]
    except subprocess.TimeoutExpired:
        return False, "docker info timed out"
    except FileNotFoundError:
        return False, "docker binary missing"


def harbor_ok() -> tuple[bool, str]:
    for cmd in ("stb", "harbor"):
        path = shutil.which(cmd)
        if path:
            return True, f"{cmd} at {path}"
    return False, "install via: uv tool install harbor  (or snorkelai-stb)"


def python_deps_ok() -> tuple[bool, str]:
    venv_lib = REPO_ROOT / ".venv-review" / "lib"
    if venv_lib.is_dir():
        for site in venv_lib.glob("python*/site-packages"):
            if (site / "pytest").is_dir():
                return True, f"Python {sys.version.split()[0]} (.venv-review)"

    missing = []
    for mod in ("pytest",):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        return False, "run: ./scripts/setup-review.sh  (or: source .venv-review/bin/activate)"
    return True, f"Python {sys.version.split()[0]}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Terminus review environment doctor")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    args = parser.parse_args()

    docker_pass, docker_detail = docker_ok()
    harbor_pass, harbor_detail = harbor_ok()
    deps_pass, deps_detail = python_deps_ok()
    req_pass = REQUIREMENTS.is_file()

    all_ok = docker_pass and harbor_pass and deps_pass and req_pass

    if args.json:
        import json

        print(
            json.dumps(
                {
                    "ok": all_ok,
                    "docker": {"ok": docker_pass, "detail": docker_detail},
                    "harbor": {"ok": harbor_pass, "detail": harbor_detail},
                    "python_deps": {"ok": deps_pass, "detail": deps_detail},
                    "requirements_txt": req_pass,
                },
                indent=2,
            )
        )
        return 0 if all_ok else 1

    print("=== Terminus doctor ===")
    check("requirements.txt present", req_pass, str(REQUIREMENTS))
    check("Python deps", deps_pass, deps_detail)
    check("Harbor / stb", harbor_pass, harbor_detail)
    check("Docker daemon", docker_pass, docker_detail)

    if not all_ok:
        print("\nFix:")
        if not req_pass or not deps_pass:
            print("  pip install -r requirements.txt")
        if not harbor_pass:
            print("  uv tool install harbor")
        if not docker_pass:
            print("  Start Docker Desktop, then: docker info")
        return 1

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
