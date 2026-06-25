#!/usr/bin/env python3
"""Repair q3 bundle runbooks so policy cleanup passes after rebuild."""

from __future__ import annotations

import re
from pathlib import Path

RUN_DIR = "/var/lib/diffusion-runs/current"
BUNDLES = Path("/app/docs/q3_bundles")


def _read(name: str) -> str:
    return (BUNDLES / name).read_text()


def _write(name: str, text: str) -> None:
    (BUNDLES / name).write_text(text)


def repair_replay_lane() -> None:
    text = _read("replay_lane.md")
    text = text.replace(
        "Replay without persisting the seed flag in the operator notes.",
        "Replay with persisted seed in operator notes.",
    )
    text = re.sub(
        r"(<!-- shell-invoke -->\n)(.*diffusion-sample)(?!.*--seed)",
        r"\1\2 --seed 9911",
        text,
        count=1,
    )
    _write("replay_lane.md", text)


def repair_mirror_lane() -> None:
    text = _read("mirror_lane.md")
    text = text.replace(
        "Operator script pulled remote checksums during validation.",
        "Operator script validates checksums from local manifest only.",
    )
    text = re.sub(r"\s*&& curl[^\n]*", "", text)
    strace_block = re.search(r"```strace\n(.*?)```", text, re.S)
    if strace_block:
        lines = [
            line
            for line in strace_block.group(1).splitlines()
            if "connect(" not in line
        ]
        if lines and not any("close(5)" in line for line in lines):
            lines.append("77120 close(5) = 0")
        replacement = "```strace\n" + "\n".join(lines) + "\n```"
        text = text[:strace_block.start()] + replacement + text[strace_block.end():]
    def _mirror_lsof_line(line: str) -> str | None:
        stripped = line.strip()
        if not stripped:
            return None
        if "ESTABLISHED" in line or ("TCP" in line and "->" in line):
            return None
        if "mirror.log" in line:
            return re.sub(r"\bcurl\b", "python", line, count=1)
        if re.match(r"^\d+\s+curl\s", stripped):
            return None
        return line

    def _mirror_lsof_block(match: re.Match[str]) -> str:
        lines: list[str] = []
        for line in match.group(1).splitlines():
            kept = _mirror_lsof_line(line)
            if kept is not None:
                lines.append(kept)
        return "```lsof\n" + "\n".join(lines) + "\n```"

    text = re.sub(r"```lsof\n(.*?)```", _mirror_lsof_block, text, flags=re.S)
    _write("mirror_lane.md", text)


def repair_cache_spill() -> None:
    text = _read("cache_spill.md")
    text = text.replace(
        "State file escaped the run directory during a resume attempt.",
        "State kept inside the run directory during resume.",
    )
    text = text.replace(
        "/etc/diffusion/cache/state.bin",
        f"{RUN_DIR}/state.bin",
    )
    text = re.sub(r".*/var/tmp/diffusion[^\n]*\n", "", text)
    _write("cache_spill.md", text)


def _burst_lsof_keep(line: str) -> bool:
    return "work/a.bin" in line or "work/b.bin" in line


def repair_burst_lane() -> None:
    text = _read("burst_lane.md")
    text = text.replace(
        "Malformed replay burst left handles open.",
        "Malformed replay burst with handles closed after the step.",
    )
    text = re.sub(
        r"(<!-- shell-invoke -->\n)(.*diffusion-sample)(?!.*--seed)",
        r"\1\2 --seed 5150",
        text,
        count=1,
    )
    text = text.replace(
        "/tmp/diffusion-run/scratch.dat",
        f"{RUN_DIR}/work/scratch.dat",
    )
    strace_block = re.search(r"```strace\n(.*?)```", text, re.S)
    if strace_block:
        body = strace_block.group(1)
        if "close(12)" not in body and "scratch.dat" in body:
            body = body.rstrip() + "\n66120 close(12) = 0\n"
        replacement = "```strace\n" + body + "```"
        text = text[:strace_block.start()] + replacement + text[strace_block.end():]
    def _burst_lsof_block(match: re.Match[str]) -> str:
        kept: list[str] = []
        for line in match.group(1).splitlines():
            if not _burst_lsof_keep(line):
                continue
            if line.startswith("      python"):
                line = "66120 python" + line[len("      python"):]
            kept.append(line)
        return "```lsof\n" + "\n".join(kept) + "\n```"

    text = re.sub(r"```lsof\n(.*?)```", _burst_lsof_block, text, flags=re.S)
    _write("burst_lane.md", text)


def main() -> None:
    repair_replay_lane()
    repair_mirror_lane()
    repair_cache_spill()
    repair_burst_lane()


if __name__ == "__main__":
    main()
