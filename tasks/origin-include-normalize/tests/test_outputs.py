import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

APP = Path("/app/environment")
BUILD_DIR = Path("/tmp/znctl-build")
BIN = BUILD_DIR / "debug" / "znctl"
MASTERS = APP / "fixtures" / "masters"
SCOPES = APP / "fixtures" / "scopes"

_CATALOG_FIELDS = ("owner", "rtype", "class", "ttl", "rdata", "key")
_EQUIV_FIELDS = ("owner", "body_digest", "zone_digest")
_APPEND_KEY = "k4"
_MX_NEW_TARGET = "mail2.example.com."
_INNER_ORIGIN_NEW = "inner.example.com."


def _fixture_inner_origin(case: str = "m2") -> str:
    text = (MASTERS / case / "inner.inc").read_text()
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("$ORIGIN"):
            anchor = line.split(None, 1)[1].strip()
            if not anchor.endswith("."):
                anchor += "."
            return anchor
    raise AssertionError("inner.inc missing $ORIGIN")


def _fixture_nest_rdata(case: str = "m2") -> str:
    text = (MASTERS / case / "inner.inc").read_text()
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[3] == "A" and "@key=nest" in line:
            return parts[4].split("@", 1)[0]
    raise AssertionError("nest A rdata not found")


def _fixture_mx_target(case: str = "m1") -> str:
    text = (MASTERS / case / "root.master").read_text()
    for line in text.splitlines():
        if " MX " in f" {line} " and "@key=k2" in line:
            parts = line.split()
            mx_idx = parts.index("MX")
            return parts[mx_idx + 2].split("@", 1)[0]
    raise AssertionError("k2 MX target not found")


def _fnv1a16(text: str) -> str:
    norm = " ".join(text.split())
    h = 0xCBF29CE484222325
    for b in norm.encode():
        h ^= b
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return f"{h:016x}"


def _fold_label(name: str, anchor: str) -> str:
    anchor = anchor.strip()
    if name.endswith("."):
        return name.lower()
    if name == "@":
        base = anchor.rstrip(".")
        return f"{base}."
    base = anchor.rstrip(".")
    return f"{name}.{base}."


def _build_body(holder: str, rtype: str, klass: str, ttl: int, rdata: str) -> str:
    return f"{holder} {rtype} {klass} {ttl} {rdata}"


def _zone_line(holder: str, klass: str, rtype: str, ttl: int, rdata: str) -> str:
    return f"{holder} {ttl} {klass} {rtype} {rdata}"


def _build_binary() -> None:
    env = os.environ.copy()
    env["CARGO_TARGET_DIR"] = str(BUILD_DIR)
    subprocess.run(
        ["cargo", "build", "--manifest-path", "/app/environment/Cargo.toml"],
        check=True,
        cwd=APP,
        env=env,
    )


@pytest.fixture(scope="session", autouse=True)
def _built_znctl() -> None:
    _build_binary()


def _workroot(tmp_path: Path, name: str) -> Path:
    dst = tmp_path / name
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    return dst


def _run_cmd(root: Path, verb: str, *rest: str) -> None:
    proc = subprocess.run(
        [str(BIN), verb, str(root), *rest],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.returncode == 0, proc.stderr


def _jsonl(path: Path) -> list[dict]:
    assert path.exists(), f"missing {path}"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _catalog(root: Path) -> list[dict]:
    return _jsonl(root / ".state" / "record-catalog.jsonl")


def _equiv(root: Path) -> list[dict]:
    return _jsonl(root / ".state" / "equiv-report.jsonl")


def _zone_lines(root: Path) -> list[str]:
    path = root / ".state" / "emitted.zone"
    assert path.exists()
    return [line for line in path.read_text().splitlines() if line.strip()]


def _reset_products(root: Path) -> None:
    state = root / ".state"
    for name in ("record-catalog.jsonl", "equiv-report.jsonl", "emitted.zone"):
        p = state / name
        if p.exists():
            p.unlink()


def _reset_journal(root: Path) -> None:
    p = root / ".state" / "scope-journal.bin"
    if p.exists():
        p.unlink()


def _reset_material(root: Path) -> None:
    p = root / ".state" / "material.bin"
    if p.exists():
        p.unlink()


def _read_scope_journal(root: Path) -> dict[str, int]:
    path = root / ".state" / "scope-journal.bin"
    if not path.exists():
        return {}
    raw = path.read_bytes()
    assert raw[:4] == b"ZNWJ"
    count = int.from_bytes(raw[5:7], "little")
    off = 7
    out: dict[str, int] = {}
    for _ in range(count):
        id_len = raw[off]
        off += 1
        key = raw[off : off + id_len].decode()
        off += id_len
        carried = raw[off]
        off += 1
        out[key] = carried
    return out


def _le_u16(raw: bytes, off: int) -> tuple[int, int]:
    return int.from_bytes(raw[off : off + 2], "little"), off + 2


def _le_u64(raw: bytes, off: int) -> tuple[int, int]:
    return int.from_bytes(raw[off : off + 8], "little"), off + 8


def _read_scope(scope_id: str) -> dict[str, tuple[int, int]]:
    raw = (SCOPES / scope_id / "seed.bin").read_bytes()
    assert raw[:4] == b"ZNLD"
    count, off = _le_u16(raw, 5)
    out: dict[str, tuple[int, int]] = {}
    for _ in range(count):
        id_len = raw[off]
        off += 1
        key = raw[off : off + id_len].decode()
        off += id_len
        pkt, off = _le_u64(raw, off)
        byte, off = _le_u64(raw, off)
        out[key] = (pkt, byte)
    return out


def _read_scope_snap(root: Path) -> tuple[list[dict], int]:
    path = root / ".state" / "scope-snap.bin"
    assert path.exists(), f"missing {path}"
    raw = path.read_bytes()
    assert raw[:4] == b"ZNSN"
    count, off = _le_u16(raw, 5)
    rows: list[dict] = []
    off = 7
    for _ in range(count):
        id_len = raw[off]
        off += 1
        key = raw[off : off + id_len].decode()
        off += id_len
        pkt, off = _le_u64(raw, off)
        byte, off = _le_u64(raw, off)
        lane = raw[off]
        off += 1
        rows.append({"key": key, "pkt": pkt, "byte": byte, "lane": lane})
    floor, _ = _le_u64(raw, off)
    return rows, floor


def _snap_floor(scope_id: str) -> int:
    seeds = _read_scope(scope_id)
    return min(pkt for pkt, _ in seeds.values()) // 5


def _catalog_key_order(root: Path) -> list[str]:
    return [row["key"] for row in _catalog(root)]


def _assert_row_digests(catalog_row: dict, equiv_row: dict) -> None:
    body = _build_body(
        catalog_row["owner"],
        catalog_row["rtype"],
        catalog_row["class"],
        catalog_row["ttl"],
        catalog_row["rdata"],
    )
    zline = _zone_line(
        catalog_row["owner"],
        catalog_row["class"],
        catalog_row["rtype"],
        catalog_row["ttl"],
        catalog_row["rdata"],
    )
    assert equiv_row["body_digest"] == _fnv1a16(body)
    assert equiv_row["zone_digest"] == _fnv1a16(zline)


def _assert_catalog_equiv_zone_align(root: Path) -> None:
    catalog = _catalog(root)
    equiv = _equiv(root)
    zone = _zone_lines(root)
    assert len(catalog) == len(equiv) == len(zone)
    for idx, crow in enumerate(catalog):
        erow = next(r for r in equiv if r["owner"] == crow["owner"])
        _assert_row_digests(crow, erow)
        assert zone[idx] == _zone_line(
            crow["owner"], crow["class"], crow["rtype"], crow["ttl"], crow["rdata"]
        )


def _material_rows_in_order(root: Path) -> list[tuple[str, int, int, str]]:
    raw = (root / ".state" / "material.bin").read_bytes()
    count, off = _le_u16(raw, 5)
    off = 7
    rows: list[tuple[str, int, int, str]] = []
    for _ in range(count):
        id_len = raw[off]
        off += 1
        key = raw[off : off + id_len].decode()
        off += id_len
        pkt, off = _le_u64(raw, off)
        byte, off = _le_u64(raw, off)
        body_len = raw[off]
        off += 1
        body = raw[off : off + body_len].decode()
        off += body_len
        rows.append((key, pkt, byte, body))
    return rows


def test_lane_a(tmp_path: Path) -> None:
    """Cold normalize must bind anchors, lane rank, scope snap, and cross-artifact digests."""
    root = _workroot(tmp_path, "lane_a")
    _run_cmd(root, "init", "m2")
    _run_cmd(root, "apply-scope", "s2")
    snap_rows, floor = _read_scope_snap(root)
    seeds = _read_scope("s2")
    assert floor == _snap_floor("s2")
    snap_by_key = {row["key"]: row for row in snap_rows}
    assert set(snap_by_key) == set(seeds)
    for key, (pkt, byte) in seeds.items():
        assert snap_by_key[key]["pkt"] == pkt
        assert snap_by_key[key]["byte"] == byte
    _reset_products(root)
    _run_cmd(root, "normalize")
    catalog = {r["key"]: r for r in _catalog(root)}
    assert set(catalog) == {"top", "nest", "deep"}
    assert _catalog_key_order(root) == ["nest", "deep", "top"]
    assert "scope-journal.bin" not in {p.name for p in (root / ".state").iterdir()}
    assert catalog["nest"]["owner"] == _fold_label("host", _fixture_inner_origin())
    assert catalog["deep"]["owner"] == _fold_label("deep", _fixture_inner_origin())
    assert catalog["top"]["owner"] == _fold_label("apex", "example.com.")
    for key in ("nest", "deep", "top"):
        pkt, _ = seeds[key]
        assert catalog[key]["ttl"] == max(pkt, floor)
        assert catalog[key]["ttl"] >= floor
    _assert_catalog_equiv_zone_align(root)


def test_lane_b(tmp_path: Path) -> None:
    """Reload must rebuild journal and catalog after journal-only and full state loss."""
    root = _workroot(tmp_path, "lane_b")
    _run_cmd(root, "init", "m3")
    _run_cmd(root, "apply-scope", "s3")
    _run_cmd(root, "normalize")
    _run_cmd(root, "reload")
    baseline_c = _catalog(root)
    baseline_e = _equiv(root)
    baseline_zone = _zone_lines(root)
    baseline_j = _read_scope_journal(root)
    assert set(baseline_j) == {"x1", "x2", "x3"}
    assert all(flag == 1 for flag in baseline_j.values())
    _reset_products(root)
    _reset_journal(root)
    _run_cmd(root, "reload")
    assert _catalog(root) == baseline_c
    assert _equiv(root) == baseline_e
    assert _zone_lines(root) == baseline_zone
    assert _read_scope_journal(root) == baseline_j
    _reset_products(root)
    _reset_journal(root)
    _reset_material(root)
    _run_cmd(root, "reload")
    assert _catalog(root) == baseline_c
    assert _equiv(root) == baseline_e
    _reset_products(root)
    _run_cmd(root, "reload")
    assert _catalog(root) == baseline_c
    assert _equiv(root) == baseline_e


def test_lane_c(tmp_path: Path) -> None:
    """Fragment anchor and rdata edits with scope rebind must preserve unrelated carry."""
    root = _workroot(tmp_path, "lane_c")
    _run_cmd(root, "init", "m2")
    _run_cmd(root, "apply-scope", "s2")
    _run_cmd(root, "normalize")
    _run_cmd(root, "reload")
    baseline = {r["key"]: r for r in _catalog(root)}
    inner_origin = _fixture_inner_origin()
    nest_old = _fixture_nest_rdata()
    nest_new = "192.0.2.99"
    inner = root / "masters" / "inner.inc"
    inner.write_text(
        inner.read_text()
        .replace(inner_origin, _INNER_ORIGIN_NEW)
        .replace(nest_old, nest_new)
    )
    _reset_products(root)
    _run_cmd(root, "reload")
    mid_c = _catalog(root)
    nest = next(r for r in mid_c if r["key"] == "nest")
    deep = next(r for r in mid_c if r["key"] == "deep")
    top = next(r for r in mid_c if r["key"] == "top")
    assert nest["owner"] == _fold_label("host", _INNER_ORIGIN_NEW)
    assert nest["rdata"] == nest_new
    assert deep["owner"] == _fold_label("deep", _INNER_ORIGIN_NEW)
    assert top["owner"] == _fold_label("apex", "example.com.")
    assert deep["ttl"] == baseline["deep"]["ttl"]
    body = _build_body(nest["owner"], nest["rtype"], nest["class"], nest["ttl"], nest_new)
    erow = next(r for r in _equiv(root) if r["owner"] == nest["owner"])
    assert erow["body_digest"] == _fnv1a16(body)
    _run_cmd(root, "apply-scope", "s2")
    _reset_products(root)
    _run_cmd(root, "reload")
    assert _catalog(root) == mid_c
    _assert_catalog_equiv_zone_align(root)
    _reset_products(root)
    _run_cmd(root, "reload")
    mid_e = _equiv(root)
    _reset_products(root)
    _run_cmd(root, "reload")
    assert _catalog(root) == mid_c
    assert _equiv(root) == mid_e


def test_lane_d(tmp_path: Path) -> None:
    """Material loss mid-workflow must re-seed totals yet keep body digests for carried rows."""
    root = _workroot(tmp_path, "lane_d")
    _run_cmd(root, "init", "m2")
    _run_cmd(root, "apply-scope", "s2")
    _run_cmd(root, "normalize")
    _run_cmd(root, "reload")
    carried_equiv = {r["owner"]: r for r in _equiv(root)}
    carried_zone = _zone_lines(root)
    material_path = root / ".state" / "material.bin"
    assert material_path.exists()
    material_path.unlink()
    _reset_products(root)
    _run_cmd(root, "reload")
    after = {r["key"]: r for r in _catalog(root)}
    seeds = _read_scope("s2")
    floor = _snap_floor("s2")
    for key in ("nest", "deep", "top"):
        pkt, _ = seeds[key]
        assert after[key]["ttl"] == max(pkt, floor)
        owner = after[key]["owner"]
        new_digest = next(r for r in _equiv(root) if r["owner"] == owner)["body_digest"]
        assert new_digest == carried_equiv[owner]["body_digest"]
    journal = _read_scope_journal(root)
    assert set(journal) == {"nest", "deep", "top"}
    assert _zone_lines(root) == carried_zone


def test_lane_e(tmp_path: Path) -> None:
    """Scope snap, material lane serialization, and catalog rows must stay mutually consistent."""
    root = _workroot(tmp_path, "lane_e")
    _run_cmd(root, "init", "m1")
    _run_cmd(root, "apply-scope", "s1")
    snap_rows, floor = _read_scope_snap(root)
    seeds = _read_scope("s1")
    assert floor == _snap_floor("s1")
    for row in snap_rows:
        pkt, byte = seeds[row["key"]]
        assert row["pkt"] == pkt
        assert row["byte"] == byte
    _run_cmd(root, "normalize")
    _reset_products(root)
    _run_cmd(root, "reload")
    material_rows = _material_rows_in_order(root)
    catalog = _catalog(root)
    equiv = _equiv(root)
    assert [key for key, _, _, _ in material_rows] == ["k1", "k2"]
    material_by_key = {key: (pkt, byte, body) for key, pkt, byte, body in material_rows}
    for row in catalog:
        pkt, byte, body = material_by_key[row["key"]]
        assert row["ttl"] == pkt
        seed_pkt, seed_byte = seeds[row["key"]]
        assert byte == seed_byte
        erow = next(r for r in equiv if r["owner"] == row["owner"])
        assert _fnv1a16(body) == erow["body_digest"]
    _assert_catalog_equiv_zone_align(root)


def test_lane_f(tmp_path: Path) -> None:
    """Appended row and MX rewrite must reconcile journal carry flags against floor and prior carry."""
    root = _workroot(tmp_path, "lane_f")
    _run_cmd(root, "init", "m1")
    _run_cmd(root, "apply-scope", "s1")
    _run_cmd(root, "normalize")
    _run_cmd(root, "reload")
    baseline = {r["key"]: r for r in _catalog(root)}
    master = root / "masters" / "root.master"
    master.write_text(
        master.read_text().rstrip()
        + f'\nextra 300 IN TXT "note" @key={_APPEND_KEY}\n'
    )
    mx_old = _fixture_mx_target()
    master.write_text(master.read_text().replace(mx_old, _MX_NEW_TARGET))
    _reset_products(root)
    _run_cmd(root, "reload")
    after = {r["key"]: r for r in _catalog(root)}
    journal = _read_scope_journal(root)
    assert journal.get("k1") == 1
    assert journal.get("k2") == 0
    assert journal.get(_APPEND_KEY) == 0
    floor = _snap_floor("s1")
    assert after[_APPEND_KEY]["ttl"] >= floor
    assert after["k1"]["ttl"] == baseline["k1"]["ttl"]
    seeds = _read_scope("s1")
    pkt, _ = seeds["k2"]
    assert after["k2"]["ttl"] == max(pkt, floor)
    k2 = after["k2"]
    body = _build_body(k2["owner"], k2["rtype"], k2["class"], k2["ttl"], f"10 {_MX_NEW_TARGET}")
    erow = next(r for r in _equiv(root) if r["owner"] == k2["owner"])
    assert erow["body_digest"] == _fnv1a16(body)
    _assert_catalog_equiv_zone_align(root)
