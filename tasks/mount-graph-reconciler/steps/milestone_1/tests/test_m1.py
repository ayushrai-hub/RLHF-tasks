import hashlib
import json
import struct
import subprocess
from pathlib import Path

REPORT = Path("/app/output/graph_report.json")
ENV = Path("/app/environment")
STUB = Path("/app/environment/fixtures/stage_stub/m3_stub.json")
SLICE_C0 = Path("/app/environment/fixtures/edge_slice/c0_a.grf")


def _prep() -> None:
    subprocess.run(["bash", "/app/environment/migrations/cln_m4.sh"], check=True)
    subprocess.run(["bash", "/app/environment/scripts/bake_m4.sh"], check=True)


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


class TestMilestone1:
    def test_m1_runner_exit_zero(self):
        """Matrix run exits zero and writes graph_report.json after cleanup and rebuild."""
        _prep()
        proc = subprocess.run(
            ["/app/bin/mgr_run", "--matrix", "--out", "/app/output/graph_report.json"],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert REPORT.is_file()

    def test_m1_c0_row_hash(self):
        """c0_base arm satisfies schema m4 and full digest chain for cluster c0."""
        _prep()
        subprocess.run(
            ["/app/bin/mgr_run", "--matrix", "--out", "/app/output/graph_report.json"],
            check=True,
        )
        doc = json.loads(REPORT.read_text(encoding="utf-8"))
        assert doc["schema_ver"] == "m4"
        arm = next(a for a in doc["arms"] if a["arm_id"] == "c0_base")
        assert hashlib.sha256(SLICE_C0.read_bytes()).hexdigest()
        assert arm["cl_tag"] == "c0"
        assert all("+c0" in tag for tag in arm["node_tags"])
        assert "a002" not in "".join(arm["node_tags"])
        _digest_chain(arm, grf_name="c0_a.grf")

    def test_m1_summary_trap(self):
        """node_tags cardinality stays below stage stub alive_count and excludes tombstoned keys."""
        stub = json.loads(STUB.read_text(encoding="utf-8"))
        assert stub["c0"]["alive_count"] == 6
        _prep()
        subprocess.run(
            ["/app/bin/mgr_run", "--matrix", "--out", "/app/output/graph_report.json"],
            check=True,
        )
        doc = json.loads(REPORT.read_text(encoding="utf-8"))
        arm = next(a for a in doc["arms"] if a["arm_id"] == "c0_base")
        assert len(arm["node_tags"]) < stub["c0"]["alive_count"]
        assert "a002" not in "".join(arm["node_tags"])
