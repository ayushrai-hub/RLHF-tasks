#!/usr/bin/env python3
from __future__ import annotations
import shutil
from pathlib import Path

def apply() -> None:
    app = Path("/app") if Path("/app/java").is_dir() else Path(__file__).resolve().parents[1] / "environment" / "app"
    fixed = Path(__file__).resolve().parent / "fixed"
    for src in fixed.rglob("*"):
        if src.is_file():
            rel = src.relative_to(fixed)
            dst = app / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

if __name__ == "__main__":
    apply()
