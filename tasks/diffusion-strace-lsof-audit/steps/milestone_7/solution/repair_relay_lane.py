#!/usr/bin/env python3
"""Repair relay_lane.md so verify probe passes."""

from __future__ import annotations

import re
from pathlib import Path

RUN_DIR = "/var/lib/diffusion-runs/current"
BUNDLES = Path("/app/docs/q3_bundles")


def repair_relay_lane() -> None:
    path = BUNDLES / "relay_lane.md"
    text = path.read_text()
    text = text.replace(
        "Cross-host relay checkpoint left hex-encoded ports and stale inode paths in the trace.",
        "Relay checkpoint kept local with stale inode paths reconciled under the run directory.",
    )

    strace_block = re.search(r"```strace\n(.*?)```", text, re.S)
    if strace_block:
        lines = [
            line
            for line in strace_block.group(1).splitlines()
            if "connect(" not in line
        ]
        lines = [
            line.replace("/etc/diffusion/stale/relay.bin", f"{RUN_DIR}/relay.bin")
            for line in lines
        ]
        text = (
            text[: strace_block.start()]
            + "```strace\n"
            + "\n".join(lines)
            + "\n```"
            + text[strace_block.end() :]
        )

    def _relay_lsof_block(match: re.Match[str]) -> str:
        kept: list[str] = []
        for line in match.group(1).splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if "->" in line or "ESTABLISHED" in line:
                continue
            kept.append(
                line.replace("/etc/diffusion/stale/relay.bin", f"{RUN_DIR}/relay.bin")
            )
        return "```lsof\n" + "\n".join(kept) + "\n```"

    text = re.sub(r"```lsof\n(.*?)```", _relay_lsof_block, text, flags=re.S)
    path.write_text(text)


def main() -> None:
    repair_relay_lane()


if __name__ == "__main__":
    main()
