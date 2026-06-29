import csv
import json
import re
import sqlite3
import subprocess
from pathlib import Path

APP = Path("/app")
OUT = APP / "output" / "p7_bundle"
CORPUS = APP / "environment" / "corpus"
DOCS = APP / "environment" / "docs"
SNAPSHOTS = DOCS / "snapshots"
API_ROOT = DOCS.joinpath("build_hints.txt").read_text(encoding="utf-8").split("http://", 1)[1].split("/health", 1)[0]
API_ROOT = f"http://{API_ROOT}"

PROFILE_IDS = DOCS.joinpath("m9_ids.txt").read_text(encoding="utf-8").strip().split(",")
COHERENT_PROFILE = PROFILE_IDS[0]
EDGE_PROFILE = PROFILE_IDS[2]
RETRY_PROFILE = PROFILE_IDS[1]
BETA_PROFILE = PROFILE_IDS[3]

T4_LANE = APP / "environment" / "rb" / "p7_pull" / "lib" / "t4_lane.rb"
R8_MARK = APP / "environment" / "net" / "r8_mark.rb"
B3_STAT = APP / "environment" / "rb" / "p7_pull" / "lib" / "b3_stat.rb"
LEVEL_MAP = {
    int(k): v
    for ln in DOCS.joinpath("k6_levels.txt").read_text(encoding="utf-8").splitlines()
    if "=" in ln
    for k, v in [ln.split("=", 1)]
}


class _patched_text:
    def __init__(self, path: Path, replacement: str):
        self.path = path
        self.replacement = replacement
        self.original = ""

    def __enter__(self):
        self.original = self.path.read_text(encoding="utf-8")
        self.path.write_text(self.replacement, encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.path.write_text(self.original, encoding="utf-8")
        return False


def _snapshot_text(index: int) -> str:
    files = sorted(p for p in SNAPSHOTS.iterdir() if p.suffix == ".rb")
    return files[index].read_text(encoding="utf-8")


PROFILE_SECTION = "[[" + "profiles]]"


def _profile_cfg(profile_id: str) -> dict:
    table = (CORPUS / "m9_table.toml").read_text(encoding="utf-8")
    block = ""
    for line in table.splitlines():
        if line.strip() == PROFILE_SECTION:
            if block and f'id = "{profile_id}"' in block:
                break
            block = ""
        block += line + "\n"
    cfg = {}
    for line in block.splitlines():
        if "=" not in line or line.strip().startswith("["):
            continue
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.strip().strip('"')
    return cfg


def _norm_ts(value: str) -> str:
    return value.replace(".000Z", "Z")


def _restart_service() -> None:
    pidfile = Path("/tmp/q9_host.pid")
    if pidfile.exists():
        pid = pidfile.read_text(encoding="utf-8").strip()
        if pid.isdigit():
            subprocess.run(["/bin/bash", "-c", f"kill {pid} 2>/dev/null || true"], check=False)
        pidfile.unlink(missing_ok=True)
    _ensure_service()


def _ensure_service() -> None:
    subprocess.run(["/app/environment/scripts/start_q9_host.sh"], check=True)
    subprocess.run(["curl", "-sf", f"{API_ROOT}/health"], check=True)


def _entry_route() -> str:
    for ln in DOCS.joinpath("bundle_contract.md").read_text(encoding="utf-8").splitlines():
        if ln.lower().startswith("index route:"):
            return ln.split(":", 1)[1].strip()
    raise RuntimeError("index route not documented")


def _encode_qs(params: dict[str, str]) -> str:
    return "&".join(f"{key}={value}" for key, value in params.items())


def _curl_batch(route: str, query: str) -> tuple[str, dict]:
    proc = subprocess.run(
        ["curl", "-sf", "-D", "-", f"{API_ROOT}{route}?{query}"],
        check=True,
        capture_output=True,
        text=True,
    )
    header, _, body = proc.stdout.partition("\r\n\r\n")
    if not body.strip():
        body = proc.stdout.split("\n\n", 1)[-1]
    hdr_next = ""
    for ln in header.splitlines():
        if ln.lower().startswith("x-next-cursor:"):
            hdr_next = ln.split(":", 1)[1].strip()
    return hdr_next, json.loads(body)


def _api_rows(since: str, until: str, band: str = "", header_only: bool = False) -> list[dict]:
    rows = []
    tok = "c0"
    route = _entry_route()
    while tok:
        query = _encode_qs({"since": since, "until": until, "prio": band, "cursor": tok})
        hdr_next, payload = _curl_batch(route, query)
        batch = payload.get("entries", [])
        rows.extend(batch)
        body_next = payload.get("next_token", "") if isinstance(payload, dict) else ""
        tok = hdr_next if header_only else (hdr_next or body_next or "")
        if not batch:
            break
    return rows


def _api_rows_body_only(since: str, until: str, band: str = "") -> list[dict]:
    rows = []
    tok = "c0"
    route = _entry_route()
    while tok:
        query = _encode_qs({"since": since, "until": until, "prio": band, "cursor": tok})
        _, payload = _curl_batch(route, query)
        batch = payload.get("entries", [])
        rows.extend(batch)
        tok = payload.get("next_token", "") if isinstance(payload, dict) else ""
        if not batch or not tok:
            break
    return rows


def _run_driver() -> None:
    if OUT.exists():
        import shutil

        shutil.rmtree(OUT)
    subprocess.run(
        [
            "bundle",
            "exec",
            "/app/rb/p7_pull/exe/p7_driver",
            "--table",
            "/app/corpus/m9_table.toml",
        ],
        cwd="/app/environment/rb/p7_pull",
        check=True,
    )


def _read_csv(profile_id: str) -> list[dict]:
    path = OUT / f"{profile_id}.csv"
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _read_db() -> list[dict]:
    conn = sqlite3.connect(OUT / "bundle.db")
    cur = conn.execute("SELECT * FROM k6_facts")
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows


def _collapse_route(path: str) -> str:
    return "/".join("{n}" if re.fullmatch(r"\d+", seg) else seg for seg in path.split("/"))


def _rollup_text() -> str:
    return (OUT / "rollup.toml").read_text(encoding="utf-8")


def _parse_rollup() -> dict:
    text = _rollup_text()
    digest_m = re.search(r'bundle_digest = "([0-9a-f]{8})"', text)
    digest = digest_m.group(1) if digest_m else ""
    groups = {}
    cur = None
    for ln in text.splitlines():
        m = re.match(r'\[groups\."(.+)"\]', ln)
        if m:
            cur = m.group(1)
            groups[cur] = {}
            continue
        if cur and "=" in ln:
            k, v = ln.split("=", 1)
            groups[cur][k.strip()] = v.strip()
    return {"bundle_digest": digest, "groups": groups}


def _bundle_digest(groups: dict) -> str:
    parts = []
    for tmpl in sorted(groups):
        g = groups[tmpl]
        share = format(float(g["err_share"]), ".6f")
        parts.append(f"{tmpl}|{g['req_total']}|{share}|{g['tail_p95_ms']}")
    payload = "\n".join(parts)
    mask64 = (1 << 64) - 1
    total = 0
    for idx, ch in enumerate(payload):
        total = (total + ((idx + 1) * ord(ch))) & mask64
    return f"{total & 0xFFFFFFFF:08x}"


def _percentile(sorted_lats: list[int], pct: float) -> int:
    if not sorted_lats:
        return 0
    rank = (pct * len(sorted_lats) + 99) // 100 - 1
    return sorted_lats[max(rank, 0)]


ERR_SHARE_TOL = 1e-6


def _err_share_equal(got: str, exp: str) -> bool:
    return abs(float(got) - float(exp)) < ERR_SHARE_TOL


def _correct_groups(csv_rows: list[dict]) -> dict:
    groups: dict[str, list[dict]] = {}
    for row in csv_rows:
        tmpl = row["route_tmpl"]
        if tmpl not in groups:
            groups[tmpl] = []
        groups[tmpl].append(row)
    out = {}
    for tmpl, grp in groups.items():
        total = len(grp)
        errs = sum(1 for r in grp if int(r["stat_cd"]) != 200)
        share = 0.0 if total == 0 else errs / total
        lats = sorted(int(r["lat_ms"]) for r in grp)
        out[tmpl] = {
            "req_total": str(total),
            "err_share": f"{share:.6f}",
            "tail_p95_ms": str(_percentile(lats, 95)),
        }
    return out


def _band_for_priority(priority: int) -> str:
    return LEVEL_MAP[priority]


def _shape_api_row(raw: dict) -> dict:
    return {
        "rec_key": raw["rec_key"],
        "route_tmpl": _collapse_route(raw["route_path"]),
        "prio_band": _band_for_priority(int(raw["priority"])),
        "rec_at": raw["recorded_at"],
        "lat_ms": int(raw["lat_ms"]),
        "stat_cd": int(raw["status_code"]),
    }


def test_k3_pipeline_live():
    """Coherent profile CSV matches a live header-driven API walk, not a short page."""
    _ensure_service()
    _run_driver()
    cfg = _profile_cfg(COHERENT_PROFILE)
    hdr_rows = _api_rows(cfg["since"], cfg["until"], header_only=True)
    csv_rows = _read_csv(COHERENT_PROFILE)
    assert len(hdr_rows) >= 20
    assert len(csv_rows) == len(hdr_rows)
    assert {r["rec_key"] for r in csv_rows} == {r["rec_key"] for r in hdr_rows}


def test_m8_full_reconciliation():
    """Every profile CSV and the shared store match API-derived row shapes and keys."""
    _ensure_service()
    _run_driver()
    db_map = {r["rec_key"]: r for r in _read_db()}
    for pid in PROFILE_IDS:
        cfg = _profile_cfg(pid)
        api_rows = _api_rows(cfg["since"], cfg["until"], cfg.get("prio", ""))
        api_by_key = {r["rec_key"]: r for r in api_rows}
        csv_rows = _read_csv(pid)
        assert len(csv_rows) == len(api_rows)
        for crow in csv_rows:
            expected = _shape_api_row(api_by_key[crow["rec_key"]])
            assert crow["route_tmpl"] == expected["route_tmpl"]
            assert crow["prio_band"] == expected["prio_band"]
            assert int(crow["lat_ms"]) == expected["lat_ms"]
            assert int(crow["stat_cd"]) == expected["stat_cd"]
            drow = db_map[crow["rec_key"]]
            assert crow["rec_at"] == drow["rec_at"]
    parsed = _parse_rollup()
    expected_groups = _correct_groups(_read_db())
    assert parsed["bundle_digest"] == _bundle_digest(expected_groups)


def test_c4_store_keys():
    """Shared store holds exactly one row per union rec_key with no extras."""
    _ensure_service()
    _run_driver()
    db_rows = _read_db()
    db_keys = [r["rec_key"] for r in db_rows]
    assert len(db_keys) == len(set(db_keys))
    union: set[str] = set()
    for pid in PROFILE_IDS:
        cfg = _profile_cfg(pid)
        union.update(r["rec_key"] for r in _api_rows(cfg["since"], cfg["until"], cfg.get("prio", "")))
    assert set(db_keys) == union


def test_a1_rollup_fields():
    """Rollup groups match route-template reductions derived from the store population."""
    _ensure_service()
    _run_driver()
    db_rows = _read_db()
    expected = _correct_groups(db_rows)
    parsed = _parse_rollup()
    assert expected, "store population is empty"
    for tmpl, exp in expected.items():
        got = parsed["groups"][tmpl]
        assert got["req_total"] == exp["req_total"]
        assert _err_share_equal(got["err_share"], exp["err_share"])
        assert got["tail_p95_ms"] == exp["tail_p95_ms"]


def test_b7_digest_from_store():
    """Bundle digest matches the header reduction over store-derived rollup groups."""
    _ensure_service()
    _run_driver()
    db_rows = _read_db()
    expected_groups = _correct_groups(db_rows)
    parsed = _parse_rollup()
    assert parsed["bundle_digest"] == _bundle_digest(expected_groups)


def test_p4_rollup_row_accounting():
    """Rollup req_total values sum to the store row count with one group per route template."""
    _ensure_service()
    _run_driver()
    db_rows = _read_db()
    parsed = _parse_rollup()
    group_total = sum(int(g["req_total"]) for g in parsed["groups"].values())
    assert group_total == len(db_rows)
    tmpl_counts: dict[str, int] = {}
    for row in db_rows:
        tmpl = row["route_tmpl"]
        tmpl_counts[tmpl] = tmpl_counts.get(tmpl, 0) + 1
    for tmpl, count in tmpl_counts.items():
        assert int(parsed["groups"][tmpl]["req_total"]) == count


def test_o4_store_union():
    """Shared store accumulates the deduplicated union of record keys across all profiles."""
    _ensure_service()
    _run_driver()
    db_keys = {r["rec_key"] for r in _read_db()}
    profile_keys: set[str] = set()
    for pid in PROFILE_IDS:
        cfg = _profile_cfg(pid)
        api = _api_rows(cfg["since"], cfg["until"], cfg.get("prio", ""))
        profile_keys.update(r["rec_key"] for r in api)
    assert profile_keys == db_keys
    assert len(db_keys) == len(_read_db())


def test_l6_tail_local_population():
    """Tail p95 latency for each route group uses only that group's latencies."""
    _ensure_service()
    _run_driver()
    db_rows = _read_db()
    groups: dict[str, list[int]] = {}
    for row in db_rows:
        tmpl = row["route_tmpl"]
        if tmpl not in groups:
            groups[tmpl] = []
        groups[tmpl].append(int(row["lat_ms"]))
    parsed = _parse_rollup()
    for tmpl, lats in groups.items():
        got = int(parsed["groups"][tmpl]["tail_p95_ms"])
        exp = _percentile(sorted(lats), 95)
        assert got == exp


def test_i7_err_status_spectrum():
    """Rollup err_share counts every non-200 status including 404 and 503 responses."""
    _ensure_service()
    _run_driver()
    db_rows = _read_db()
    non200_codes = {int(r["stat_cd"]) for r in db_rows if int(r["stat_cd"]) != 200}
    assert 404 in non200_codes
    assert non200_codes & {500, 503}
    expected = _correct_groups(db_rows)
    parsed = _parse_rollup()
    for tmpl, exp in expected.items():
        got = parsed["groups"][tmpl]
        assert _err_share_equal(got["err_share"], exp["err_share"])


def test_h4_body_hdr_divergence():
    """Coherent harvest must follow header continuation, not the body token channel."""
    _ensure_service()
    cfg = _profile_cfg(COHERENT_PROFILE)
    hdr_rows = _api_rows(cfg["since"], cfg["until"], header_only=True)
    body_rows = _api_rows_body_only(cfg["since"], cfg["until"])
    assert len(body_rows) < len(hdr_rows)
    _run_driver()
    csv_keys = {r["rec_key"] for r in _read_csv(COHERENT_PROFILE)}
    assert csv_keys == {r["rec_key"] for r in hdr_rows}


def test_e9_restart_stable():
    """Bundle outputs stay identical across API restart and consecutive driver runs."""
    _restart_service()
    _run_driver()
    first_roll = _rollup_text()
    first_db = (OUT / "bundle.db").read_bytes()
    _restart_service()
    _run_driver()
    assert _rollup_text() == first_roll
    assert (OUT / "bundle.db").read_bytes() == first_db


def test_q3_rollout_union_keys():
    """Each profile CSV is duplicate-free and profile key unions match the store."""
    _ensure_service()
    _run_driver()
    csv_union: set[str] = set()
    for pid in PROFILE_IDS:
        keys = [r["rec_key"] for r in _read_csv(pid)]
        assert len(keys) == len(set(keys)), f"{pid} csv has duplicate keys"
        csv_union.update(keys)
    db_keys = {r["rec_key"] for r in _read_db()}
    assert db_keys == csv_union


def test_r7_s03_half_open():
    """Narrow-window CSV rows all fall inside the half-open profile window."""
    _ensure_service()
    _run_driver()
    cfg = _profile_cfg(EDGE_PROFILE)
    since_t = _norm_ts(cfg["since"])
    until_t = _norm_ts(cfg["until"])
    for crow in _read_csv(EDGE_PROFILE):
        at = _norm_ts(crow["rec_at"])
        assert at >= since_t
        assert at < until_t


def test_u5_cross_sink_mirrors():
    """CSV and SQL rec_at, lat_ms, and stat_cd agree for every shared record key."""
    _ensure_service()
    _run_driver()
    db_map = {r["rec_key"]: r for r in _read_db()}
    for pid in PROFILE_IDS:
        for crow in _read_csv(pid):
            drow = db_map[crow["rec_key"]]
            assert crow["rec_at"] == drow["rec_at"]
            assert int(crow["lat_ms"]) == int(drow["lat_ms"])
            assert int(crow["stat_cd"]) == int(drow["stat_cd"])


def test_j3_s03_subset():
    """Narrow-window profile rows match API and stay within the coherent key set."""
    _ensure_service()
    _run_driver()
    narrow_id = PROFILE_IDS[2]
    cfg = _profile_cfg(narrow_id)
    api_rows = _api_rows(cfg["since"], cfg["until"], cfg.get("prio", ""))
    api_by_key = {r["rec_key"]: r for r in api_rows}
    csv_rows = _read_csv(narrow_id)
    coherent_keys = {r["rec_key"] for r in _read_csv(COHERENT_PROFILE)}
    assert len(csv_rows) == len(api_rows)
    for crow in csv_rows:
        assert crow["rec_key"] in coherent_keys
        expected = _shape_api_row(api_by_key[crow["rec_key"]])
        assert crow["route_tmpl"] == expected["route_tmpl"]
        assert crow["prio_band"] == expected["prio_band"]
        assert int(crow["lat_ms"]) == expected["lat_ms"]
        assert int(crow["stat_cd"]) == expected["stat_cd"]


def test_w4_span():
    """Coherent profile retrieves the full seeded corpus for its window."""
    _ensure_service()
    _run_driver()
    cfg = _profile_cfg(COHERENT_PROFILE)
    api = _api_rows(cfg["since"], cfg["until"])
    csv_rows = _read_csv(COHERENT_PROFILE)
    assert len(csv_rows) == len(api)
    assert len(api) == 20


def test_q8_cursor_header_chain():
    """Coherent profile matches API walk that advances only via response headers."""
    _ensure_service()
    _run_driver()
    cfg = _profile_cfg(COHERENT_PROFILE)
    api_hdr = _api_rows(cfg["since"], cfg["until"], header_only=True)
    csv_rows = _read_csv(COHERENT_PROFILE)
    assert len(csv_rows) == len(api_hdr)
    api_keys = {r["rec_key"] for r in api_hdr}
    csv_keys = {r["rec_key"] for r in csv_rows}
    assert api_keys == csv_keys


def test_z1_dup():
    """Retry profile does not inflate row count after the 503 sequence."""
    _ensure_service()
    _run_driver()
    cfg = _profile_cfg(RETRY_PROFILE)
    api = _api_rows(cfg["since"], cfg["until"])
    csv_rows = _read_csv(RETRY_PROFILE)
    assert len(csv_rows) == len(api)
    assert len(csv_rows) == len({r["rec_key"] for r in csv_rows})


def test_k9_retry_keys_unique():
    """Retry profile emits each API rec_key once with no duplicate rows."""
    _ensure_service()
    _run_driver()
    cfg = _profile_cfg(RETRY_PROFILE)
    api = _api_rows(cfg["since"], cfg["until"])
    csv_rows = _read_csv(RETRY_PROFILE)
    keys = [r["rec_key"] for r in csv_rows]
    assert len(keys) == len(set(keys))
    assert len(csv_rows) == len(api)
    assert set(keys) == {r["rec_key"] for r in api}


def test_g7_glitch_batch_once():
    """Rows from the glitch batch token appear exactly once after retry recovery."""
    _restart_service()
    _run_driver()
    cfg = _profile_cfg(RETRY_PROFILE)
    full_api = _api_rows(cfg["since"], cfg["until"])
    glitch_keys = {r["rec_key"] for r in full_api[7:11]}
    assert glitch_keys, "expected a four-row glitch slice in the seeded corpus"
    db_counts: dict[str, int] = {}
    for row in _read_db():
        db_counts[row["rec_key"]] = db_counts.get(row["rec_key"], 0) + 1
    csv_counts: dict[str, int] = {}
    for row in _read_csv(RETRY_PROFILE):
        csv_counts[row["rec_key"]] = csv_counts.get(row["rec_key"], 0) + 1
    for key in glitch_keys:
        assert db_counts.get(key, 0) == 1
        assert csv_counts.get(key, 0) == 1


def test_h8_edge():
    """Window profile excludes the row sitting on the half-open end instant."""
    _ensure_service()
    _run_driver()
    cfg = _profile_cfg(EDGE_PROFILE)
    api = _api_rows(cfg["since"], cfg["until"])
    keys = {r["rec_key"] for r in _read_csv(EDGE_PROFILE)}
    until_t = cfg["until"]
    wide = _api_rows(cfg["since"], _profile_cfg(COHERENT_PROFILE)["until"])
    edge_keys = [r["rec_key"] for r in wide if _norm_ts(r["recorded_at"]) == _norm_ts(until_t)]
    assert len(edge_keys) == 1
    assert edge_keys[0] not in keys
    assert len(keys) == len(api)


def test_y7_beta_subset():
    """Beta-filtered keys are a proper subset of the unfiltered API window."""
    _ensure_service()
    _run_driver()
    cfg = _profile_cfg(BETA_PROFILE)
    api_filtered = _api_rows(cfg["since"], cfg["until"], cfg["prio"])
    api_wide = _api_rows(cfg["since"], cfg["until"])
    filtered_keys = {r["rec_key"] for r in api_filtered}
    wide_keys = {r["rec_key"] for r in api_wide}
    csv_keys = {r["rec_key"] for r in _read_csv(BETA_PROFILE)}
    assert filtered_keys <= wide_keys
    assert csv_keys == filtered_keys
    assert {r["prio_band"] for r in _read_csv(BETA_PROFILE)} == {"beta"}


def test_n2_gate():
    """Filtered profile emits only the beta band and matches the filtered API window."""
    _ensure_service()
    _run_driver()
    cfg = _profile_cfg(BETA_PROFILE)
    api = _api_rows(cfg["since"], cfg["until"], cfg["prio"])
    csv_rows = _read_csv(BETA_PROFILE)
    assert len(csv_rows) == len(api)
    assert {r["prio_band"] for r in csv_rows} == {"beta"}
    coherent_bands = {r["prio_band"] for r in _read_csv(COHERENT_PROFILE)}
    assert len(coherent_bands) >= 3


def test_s5_since_inclusive():
    """Rows at the inclusive since instant appear in the coherent profile."""
    _ensure_service()
    _run_driver()
    cfg = _profile_cfg(COHERENT_PROFILE)
    api_rows = _api_rows(cfg["since"], cfg["until"])
    csv_keys = {r["rec_key"] for r in _read_csv(COHERENT_PROFILE)}
    earliest = min(api_rows, key=lambda r: r["recorded_at"])
    assert earliest["rec_key"] in csv_keys
    assert len(csv_keys) == len(api_rows)


def test_p9_grid():
    """Route grouping on coherent profile matches the collapse rule from the stat header."""
    _ensure_service()
    _run_driver()
    cfg = _profile_cfg(COHERENT_PROFILE)
    api = _api_rows(cfg["since"], cfg["until"])
    expected = {_collapse_route(e["route_path"]) for e in api}
    csv_tmpls = {r["route_tmpl"] for r in _read_csv(COHERENT_PROFILE)}
    assert csv_tmpls == expected


def test_u1_prio_mapping():
    """Priority band tokens in CSV rows match the public numeric mapping file."""
    _ensure_service()
    _run_driver()
    cfg = _profile_cfg(COHERENT_PROFILE)
    api_by_key = {r["rec_key"]: r for r in _api_rows(cfg["since"], cfg["until"])}
    for row in _read_csv(COHERENT_PROFILE):
        pri = int(api_by_key[row["rec_key"]]["priority"])
        assert row["prio_band"] == _band_for_priority(pri)


def test_t0_idem():
    """Consecutive driver runs emit identical bundle trees."""
    _ensure_service()
    _run_driver()
    first_csv = (OUT / f"{COHERENT_PROFILE}.csv").read_text(encoding="utf-8")
    first_roll = _rollup_text()
    first_db = (OUT / "bundle.db").read_bytes()
    _run_driver()
    second_csv = (OUT / f"{COHERENT_PROFILE}.csv").read_text(encoding="utf-8")
    second_roll = _rollup_text()
    second_db = (OUT / "bundle.db").read_bytes()
    assert first_csv == second_csv
    assert first_roll == second_roll
    assert first_db == second_db


def test_v6_ablate_a():
    """Paginated fetches on the coherent profile must walk the full corpus via header continuation."""
    _ensure_service()
    baseline = _snapshot_text(0)
    with _patched_text(T4_LANE, baseline):
        _run_driver()
        cfg = _profile_cfg(COHERENT_PROFILE)
        api = _api_rows(cfg["since"], cfg["until"])
        api_hdr = _api_rows(cfg["since"], cfg["until"], header_only=True)
        csv_rows = _read_csv(COHERENT_PROFILE)
        span_bad = len(csv_rows) != len(api) or len(csv_rows) < 10
        hdr_bad = len(csv_rows) != len(api_hdr) or {r["rec_key"] for r in csv_rows} != {
            r["rec_key"] for r in api_hdr
        }
        assert span_bad or hdr_bad


def test_v6_ablate_b():
    """Retry profile must not duplicate rows after upstream hiccups or leak priority-filtered bands."""
    _restart_service()
    baseline = _snapshot_text(1)
    with _patched_text(R8_MARK, baseline):
        _run_driver()
        retry_rows = _read_csv(RETRY_PROFILE)
        cfg = _profile_cfg(RETRY_PROFILE)
        api = _api_rows(cfg["since"], cfg["until"])
        beta_bands = {r["prio_band"] for r in _read_csv(BETA_PROFILE)}
        dup_keys = len(retry_rows) != len({r["rec_key"] for r in retry_rows})
        glitch_keys = {r["rec_key"] for r in api[7:11]}
        glitch_dup = any(
            sum(1 for r in retry_rows if r["rec_key"] == k) != 1 for k in glitch_keys
        )
        assert dup_keys or len(retry_rows) != len(api) or beta_bands != {"beta"} or glitch_dup


def test_v6_ablate_c():
    """CSV instants and rollup metrics must stay aligned with SQL rows on the coherent profile."""
    _restart_service()
    baseline = _snapshot_text(2)
    with _patched_text(B3_STAT, baseline):
        _run_driver()
        csv_rows = _read_csv(COHERENT_PROFILE)
        assert csv_rows, "coherent profile produced no csv rows"
        parsed = _parse_rollup()
        expected = _bundle_digest(_correct_groups(_read_db()))
        db_rows = {r["rec_key"]: r for r in _read_db()}
        misaligned = any(
            crow["rec_at"] != db_rows[crow["rec_key"]]["rec_at"] for crow in csv_rows
        )
        bad_digest = parsed["bundle_digest"] != expected
        bad_rollup = any(
            not _err_share_equal(
                parsed["groups"][tmpl]["err_share"],
                _correct_groups(_read_db()).get(tmpl, {}).get("err_share", "0"),
            )
            for tmpl in parsed["groups"]
        )
        assert misaligned or bad_digest or bad_rollup
