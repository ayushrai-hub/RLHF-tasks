"""
Seed-driven adversarial shard mutator for x12-837-claim-loop-weaver.
"""

from __future__ import annotations

import json
import random
from pathlib import Path


def _isa(elem: str = "*", comp: str = ":") -> str:
    f02 = " " * 10
    f04 = " " * 10
    f06 = "SUBMITTER".ljust(15)
    f08 = "RECEIVER".ljust(15)
    body = elem.join(
        [
            "ISA",
            "00",
            f02,
            "00",
            f04,
            "ZZ",
            f06,
            "ZZ",
            f08,
            "230101",
            "1200",
            "^",
            "00501",
            "000000001",
            "1",
            "P",
            comp,
        ]
    )
    return body + "~"


def _nm1(elem: str, qualifier: str, last: str, first: str, member_id: str) -> str:
    return elem.join(["NM1", qualifier, "1", last, first, "", "", "", "MI", member_id]) + "~"


def run_mutate(seed: str, shards_dir: Path) -> None:
    rng = random.Random(seed)
    shards_dir.mkdir(parents=True, exist_ok=True)
    for path in shards_dir.glob("*.edi"):
        path.unlink()

    elem = "|" if rng.random() < 0.5 else "*"

    east = (
        _isa(elem)
        + elem.join(["CLM", "ADV100", "400.00", "", "", "11:B:1", "Y*A*Y*Y"])
        + "~"
        + _nm1(elem, "QC", "CASE", "ALPHA", "PAT900")
        + _nm1(elem, "IL", "CASE", "ALPHA", "SUB900")
        + elem.join(["LX", "2"])
        + "~"
        + elem.join(["SV1", "HC:99214", "200.00", "UN", "1", "", "", "2"])
        + "~"
        + elem.join(["LX", "1"])
        + "~"
        + elem.join(["SV1", "HC:99213", "200.00", "UN", "1", "", "", "1"])
        + "~"
        + elem.join(["HI", "ABK:E11.9"])
        + "~"
    )
    (shards_dir / "biller-east.edi").write_text(east, encoding="utf-8")

    west = (
        _isa(elem)
        + elem.join(["CLM", "ADV200", "150.00", "", "", "11:B:1", "Y*A*Y*Y"])
        + "~"
        + _nm1(elem, "QC", "CASE", "BETA", "PAT901")
        + elem.join(["LX", "1"])
        + "~"
        + elem.join(["SV1", "HC:99215", "150.00", "UN", "1", "", "", "1"])
        + "~"
    )
    (shards_dir / "biller-west.edi").write_text(west, encoding="utf-8")

    manifest = {
        "biller-east.edi": 20,
        "biller-west.edi": 30,
    }
    (shards_dir.parent / "shard-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
