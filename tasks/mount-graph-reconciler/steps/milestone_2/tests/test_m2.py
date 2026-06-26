import hashlib
import json
import struct
import subprocess
from pathlib import Path

REPORT = Path("/app/output/graph_report.json")
ENV = Path("/app/environment")

ARM_GRf = {"c1_var": "c1_a.grf", "c2_var": "c2_a.grf"}


def _prep() -> None:
    subprocess.run(["bash", "/app/environment/migrations/cln_m4.sh"], check=True)
    subprocess.run(["bash", "/app/environment/scripts/bake_m4.sh"], check=True)


def _run_chk() -> None:
    subprocess.run(
        ["/app/bin/mgr_run", "--matrix", "--out", "/app/output/graph_report.json"],
        check=True,
    )


def _load_base_slots() -> dict[str, str]:
    raw = (ENV / "fixtures" / "tab_frag" / "fs0.tab").read_bytes()
    slots: dict[str, str] = {}
    if len(raw) < 7 or raw[:4] != b"LAYS":
        return slots
    count = struct.unpack(">H", raw[5:7])[0]
    pos = 7
    for _ in range(count):
        key = raw[pos : pos + 4].decode("ascii", errors="replace").strip(chr(0))
        slots[key] = chr(raw[pos + 4])
        pos += 5
    return slots


def _slice_alive_keys(grf_name: str) -> list[str]:
    buf = (ENV / "fixtures" / "edge_slice" / grf_name).read_bytes()
    alive: list[str] = []
    if len(buf) < 9 or buf[:4] != b"GRFX":
        return alive
    count = struct.unpack(">H", buf[7:9])[0]
    pos = 9
    for _ in range(count):
        key = buf[pos : pos + 4].decode("ascii", errors="replace").strip(chr(0))
        state = chr(buf[pos + 4])
        pos += 5
        if state != "T":
            alive.append(key)
    return alive


def _expected_path_a_hex(grf_name: str) -> str:
    base = _load_base_slots()
    slots = dict(base)
    for key in _slice_alive_keys(grf_name):
        if slots.get(key) == "T":
            continue
        slots[key] = "A"
    for key, marker in base.items():
        if marker == "T":
            slots[key] = marker
    slot_parts = [f"{k}:{v}" for k, v in sorted(slots.items())]
    return hashlib.sha256("|".join(slot_parts).encode("ascii")).hexdigest()


def _tombstoned_keys(grf_name: str) -> set[str]:
    buf = (ENV / "fixtures" / "edge_slice" / grf_name).read_bytes()
    keys: set[str] = set()
    if len(buf) < 9 or buf[:4] != b"GRFX":
        return keys
    count = struct.unpack(">H", buf[7:9])[0]
    pos = 9
    for _ in range(count):
        key = buf[pos : pos + 4].decode("ascii", errors="replace").strip(chr(0))
        state = chr(buf[pos + 4])
        pos += 5
        if state == "T":
            keys.add(key)
    return keys


def _digest_chain(arm: dict, *, grf_name: str) -> None:
    expected_a = _expected_path_a_hex(grf_name)
    assert arm["path_a_hex"] == expected_a
    path_b = hashlib.sha256("".join(arm["node_tags"]).encode("ascii")).hexdigest()
    assert arm["path_b_hex"] == path_b
    cross = hashlib.sha256(
        f"{expected_a}|{path_b}|{arm['cl_tag']}".encode("ascii")
    ).hexdigest()
    assert arm["cross_link"] == cross
    digest_src = f"{arm['cl_tag']}|" + "|".join(sorted(arm["node_tags"])) + f"|{cross}"
    assert arm["row_digest"] == hashlib.sha256(digest_src.encode("ascii")).hexdigest()


class TestMilestone2:
    def test_m2_marker_guard(self):
        """Variant arms exclude tombstoned edge keys while tagging survivors with cluster ids."""
        _prep()
        _run_chk()
        doc = json.loads(REPORT.read_text(encoding="utf-8"))
        c1 = next(a for a in doc["arms"] if a["arm_id"] == "c1_var")
        c2 = next(a for a in doc["arms"] if a["arm_id"] == "c2_var")
        for arm, grf, tag in ((c1, "c1_a.grf", "c1"), (c2, "c2_a.grf", "c2")):
            tombs = _tombstoned_keys(grf)
            joined = "".join(arm["node_tags"])
            assert all(t not in joined for t in tombs)
            assert all(f"+{tag}" in t for t in arm["node_tags"])

    def test_m2_dual_path_hex(self):
        """c1 and c2 arms publish independent path_a_hex and path_b_hex digests."""
        _prep()
        _run_chk()
        doc = json.loads(REPORT.read_text(encoding="utf-8"))
        for arm_id in ("c1_var", "c2_var"):
            arm = next(a for a in doc["arms"] if a["arm_id"] == arm_id)
            grf = ARM_GRf[arm_id]
            assert arm["path_a_hex"] == _expected_path_a_hex(grf)
            assert arm["path_a_hex"] != arm["path_b_hex"]
            expected_b = hashlib.sha256("".join(arm["node_tags"]).encode("ascii")).hexdigest()
            assert arm["path_b_hex"] == expected_b

    def test_m2_link_derive_hex(self):
        """Variant arms satisfy cross_link and row_digest derivation from path digests."""
        _prep()
        _run_chk()
        doc = json.loads(REPORT.read_text(encoding="utf-8"))
        for arm_id in ("c1_var", "c2_var"):
            arm = next(a for a in doc["arms"] if a["arm_id"] == arm_id)
            _digest_chain(arm, grf_name=ARM_GRf[arm_id])
