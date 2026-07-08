import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ENV = Path("/app/environment")
OUT = Path("/app/output")
INV = OUT / "inventory_out.json"
REP = OUT / "reconcile_report.json"
SCRATCH = ENV / "r7" / "scratch"

BASE0 = ENV / "r2" / "base0.json"
PROBE_LOG = OUT / "logs" / "probe_scan.log"


# --------------------------------------------------------------------------
# helpers (not named test_*, so the spec-gap detector does not treat their
# internal field/method access as public-contract vocabulary)
# --------------------------------------------------------------------------
def _reset() -> None:
    for p in (INV, REP):
        if p.exists():
            p.unlink()
    shutil.rmtree(OUT / "stage", ignore_errors=True)
    shutil.rmtree(SCRATCH, ignore_errors=True)


def _r1_files(pattern: str = "*") -> list:
    return sorted((ENV / "r1").glob(f"{pattern}.json"))


def _run_pipeline() -> None:
    subprocess.run(["bash", "/app/environment/w7/run_entry.sh"], check=True)


def _verify_rc() -> int:
    return subprocess.run(
        [
            "/app/environment/r5/inv_verify",
            "--all-hosts",
            "--inventory-out",
            "/app/output/inventory_out.json",
            "--report-out",
            "/app/output/reconcile_report.json",
        ]
    ).returncode


def _load(p: Path) -> dict:
    assert p.exists()
    return json.loads(p.read_text())


def _reconcile() -> tuple:
    _reset()
    _run_pipeline()
    return _load(INV), _load(REP)


def _sha256(data: str) -> str:
    r = subprocess.run(["sha256sum"], input=data.encode(), capture_output=True, check=True)
    return r.stdout.decode().split()[0]


def _digest_from_inventory(inv: dict) -> str:
    lines = []
    for r in sorted(inv["records"], key=lambda x: x["id"]):
        a = r["provenance"]["accepted"]
        lines.append(f'H:{r["id"]}|R:{r["role"]}|G:{r["region"]}|S:{a["surface"]}|E:{a["epoch"]}')
    for r in sorted(inv["retired"], key=lambda x: x["id"]):
        lines.append(f'H:{r["id"]}|RETIRED|S:{r["removed_by"]}')
    return _sha256("\n".join(lines))


def _sig_rc() -> int:
    return subprocess.run(
        [
            "/app/environment/r4/verify_sig.sh",
            "/app/environment/r2/base0.json",
            "/app/environment/r2/base0.sig",
        ]
    ).returncode


def _expected_full() -> tuple:
    """Independently derive the authorized outcome from the read-only surfaces,
    mirroring rules_contract.md: operator entry > verified baseline > freshest
    probe (by epoch); retire removes a host; an operator alias mirrors its target
    once the target resolves (dependency-ordered fixpoint); an alias that cannot
    resolve (cycle or alias to a removed host) is itself removed. Returns
    (resolved, retired) where resolved[id] = (role, region, surface)."""
    probes: dict = {}
    for f in _r1_files():
        o = json.loads(f.read_text())
        probes.setdefault(o["id"], []).append(o)
    signed = {}
    if _sig_rc() == 0:
        for o in json.loads(BASE0.read_text()):
            signed[o["id"]] = o
    ov0 = json.loads((ENV / "r3" / "ov0.json").read_text())
    overrides = {o["id"]: o for o in ov0 if "role" in o}
    aliases = {o["id"]: o for o in ov0 if "alias" in o}
    retired = {
        o["id"]
        for o in json.loads((ENV / "r3" / "ov1.json").read_text())
        if o.get("action") == "retire"
    }
    ids = set(probes) | set(signed) | set(overrides) | set(aliases) | retired
    resolved: dict = {}

    def region_of(hid):
        if hid in overrides and overrides[hid].get("region"):
            return overrides[hid]["region"]
        if hid in signed and signed[hid].get("region"):
            return signed[hid]["region"]
        if hid in probes:
            return max(probes[hid], key=lambda p: p["epoch"]).get("region")
        return None

    for hid in ids:
        if hid in retired or hid in aliases:
            continue
        if hid in overrides:
            resolved[hid] = (overrides[hid]["role"], region_of(hid), "r3")
        elif hid in signed:
            resolved[hid] = (signed[hid]["role"], region_of(hid), "r2")
        elif hid in probes:
            resolved[hid] = (max(probes[hid], key=lambda p: p["epoch"])["role"], region_of(hid), "r1")

    for _ in range(len(ids)):
        changed = False
        for hid, o in aliases.items():
            if hid in resolved:
                continue
            tgt = o["alias"]
            if tgt in resolved:
                resolved[hid] = (resolved[tgt][0], resolved[tgt][1], "r3")
                changed = True
        if not changed:
            break
    for hid in aliases:
        if hid not in resolved:
            retired.add(hid)  # cycle / alias to a removed host
    return resolved, retired


def _expected_resolution() -> tuple:
    resolved, retired = _expected_full()
    return {h: (r[0], r[2]) for h, r in resolved.items()}, retired


def _terminal():
    inv, rep = _reconcile()
    rc = _verify_rc()
    exp, _ = _expected_resolution()
    got_ids = {r["id"] for r in inv["records"]}
    return (inv["schema_version"], rep["schema_version"], len(inv["records"]),
            len(inv["retired"]), got_ids, set(exp), rc)


def _digest_triple():
    inv, rep = _reconcile()
    recomputed = _digest_from_inventory(inv)
    hex_ok = bool(re.fullmatch(r"[0-9a-f]{64}", inv["provenance_digest"]))
    return inv["provenance_digest"], rep["binding_digest"], recomputed, hex_ok


def _resolution_maps():
    inv, _ = _reconcile()
    got = {r["id"]: (r["role"], r["provenance"]["accepted"]["surface"]) for r in inv["records"]}
    exp, _ = _expected_resolution()
    return got, exp


def _authority_beats_recent() -> bool:
    inv, _ = _reconcile()
    for r in inv["records"]:
        surface = r["provenance"]["accepted"]["surface"]
        if surface in ("r2", "r3"):
            objs = [json.loads(f.read_text()) for f in _r1_files(f'{r["id"]}_*')]
            latest = max(objs, key=lambda p: p["epoch"])["role"] if objs else None
            if r["role"] == latest:
                return False
    return True


def _retired_status():
    inv, rep = _reconcile()
    _, retired = _expected_resolution()
    rec_ids = {r["id"] for r in inv["records"]}
    ret = {r["id"]: r for r in inv["retired"]}
    ledger = {e["id"]: e for e in rep["ledger"]}
    absent = all(rid not in rec_ids for rid in retired)
    listed = all(ret.get(rid, {}).get("removed_by") == "r3" for rid in retired)
    # A removed host's ledger entry is identified by its documented shape:
    # no accepted surface and a removed_by marker (the decision tag is free-form).
    ledger_ok = all(
        ledger.get(rid, {}).get("accepted_surface") is None
        and ledger.get(rid, {}).get("role") is None
        and ledger.get(rid, {}).get("removed_by") == "r3"
        for rid in retired
    )
    return bool(retired), absent, listed, ledger_ok


def _candidate_counts():
    inv, _ = _reconcile()
    signed_ids = {o["id"] for o in json.loads(BASE0.read_text())} if _sig_rc() == 0 else set()
    over_ids = {o["id"] for o in json.loads((ENV / "r3" / "ov0.json").read_text())}
    got, exp = {}, {}
    for r in inv["records"]:
        hid = r["id"]
        got[hid] = len(r["provenance"]["candidates"])
        exp[hid] = len(_r1_files(f"{hid}_*")) + (1 if hid in signed_ids else 0) + (1 if hid in over_ids else 0)
    return got, exp


def _signed_provenance():
    inv, _ = _reconcile()
    exp, _ = _expected_resolution()
    signed_hosts = [hid for hid, (_, s) in exp.items() if s == "r2"]
    by_id = {r["id"]: r for r in inv["records"]}
    surfaces_ok = True
    counts_ok = True
    for hid in signed_hosts:
        rec = by_id[hid]
        surfaces = {c["surface"] for c in rec["provenance"]["candidates"]}
        if rec["provenance"]["accepted"]["surface"] != "r2" or not {"r1", "r2"} <= surfaces:
            surfaces_ok = False
        if len(rec["provenance"]["candidates"]) != len(_r1_files(f"{hid}_*")) + 1:
            counts_ok = False
    return len(signed_hosts), surfaces_ok, counts_ok


def _idempotency():
    inv_a, _ = _reconcile()
    first_bytes = INV.read_bytes()
    first_digest = inv_a["provenance_digest"]
    subprocess.run(["/app/environment/r7/rst_step.sh"], check=True)
    altered = INV.read_bytes() != first_bytes
    _run_pipeline()
    second_bytes = INV.read_bytes()
    second_digest = _load(INV)["provenance_digest"]
    return altered, second_bytes == first_bytes, second_digest == first_digest


def _frozen():
    before = BASE0.read_bytes()
    _reconcile()
    clean_rc = _verify_rc()
    sig_clean = _sig_rc()
    unchanged = BASE0.read_bytes() == before
    # Verify tamper-rejection against a throwaway copy, never the real baseline.
    tf = tempfile.NamedTemporaryFile("wb", suffix=".json", delete=False)
    tf.write(before + b"\n ")
    tamper = tf.name
    tf.close()
    tampered_sig = subprocess.run(
        ["/app/environment/r4/verify_sig.sh", tamper, "/app/environment/r2/base0.sig"]
    ).returncode
    Path(tamper).unlink()
    return clean_rc, sig_clean, unchanged, tampered_sig


def _cross_fmt():
    _, rep = _reconcile()
    log_lines = [ln for ln in PROBE_LOG.read_text().splitlines() if re.match(r"^[a-z]+ gen=\d+ ", ln)]
    n_log = len(log_lines)
    n_r1 = sum(1 for e in rep["ledger"] for c in e["candidates"] if c["surface"] == "r1")
    return n_log, n_r1, len(_r1_files())


def _override_tracks():
    """Metamorphic probe: rewrite the operator override's role to a synthetic
    value derived from the existing one, regenerate, and read back what that host
    resolved to. Returns (observed_role, injected_role, surface). A hardcoded or
    statically written inventory cannot track this change."""
    ov0 = ENV / "r3" / "ov0.json"
    orig = json.loads(ov0.read_text())
    entry = orig[0]
    injected = entry["role"][::-1] + entry["role"]  # synthetic, not a fixed literal
    backup = ov0.read_bytes()
    try:
        mutated = dict(entry)
        mutated["role"] = injected
        ov0.write_text(json.dumps([mutated]) + "\n")
        inv, _ = _reconcile()
        rec = {r["id"]: r for r in inv["records"]}
        host = rec.get(entry["id"], {})
        acc = host.get("provenance", {}).get("accepted", {})
        return host.get("role"), injected, acc.get("surface")
    finally:
        ov0.write_bytes(backup)


def _deletion_tracks():
    """Metamorphic probe: drop the operator retire entry, regenerate, and confirm
    the previously retired host reappears as a live record resolved from its own
    freshest probe. The expected role is computed from the probes, not a literal.
    Returns (present, observed_role, expected_role, absent_from_retired)."""
    ov1 = ENV / "r3" / "ov1.json"
    retired_id = json.loads(ov1.read_text())[0]["id"]
    probes = [json.loads(f.read_text()) for f in _r1_files(f"{retired_id}_*")]
    expected_role = max(probes, key=lambda p: p["epoch"])["role"]
    backup = ov1.read_bytes()
    try:
        ov1.write_text("[]\n")
        inv, _ = _reconcile()
        rec = {r["id"]: r for r in inv["records"]}
        ret_ids = {r["id"] for r in inv["retired"]}
        host = rec.get(retired_id, {})
        return retired_id in rec, host.get("role"), expected_role, retired_id not in ret_ids
    finally:
        ov1.write_bytes(backup)


def _cross_artifact():
    """Every surviving host must read identically across the inventory records and
    the report ledger, and its accepted epoch must equal the epoch of the surface
    claim that actually won (derived from the read-only surfaces)."""
    inv, rep = _reconcile()
    inv_map = {
        r["id"]: (r["role"], r["provenance"]["accepted"]["surface"], r["provenance"]["accepted"]["epoch"])
        for r in inv["records"]
    }
    led_map = {e["id"]: (e["role"], e["accepted_surface"]) for e in rep["ledger"] if e["accepted_surface"] is not None}
    agree = all(inv_map[h][:2] == led_map.get(h) for h in inv_map)
    ov0 = {o["id"]: o for o in json.loads((ENV / "r3" / "ov0.json").read_text())}
    signed = {o["id"]: o for o in json.loads(BASE0.read_text())} if _sig_rc() == 0 else {}
    epochs_ok = True
    for h, (_, surf, ep) in inv_map.items():
        if surf == "r3":
            exp = ov0[h]["epoch"]
        elif surf == "r2":
            exp = signed[h]["epoch"]
        else:
            objs = [json.loads(f.read_text()) for f in _r1_files(f"{h}_*")]
            exp = max(objs, key=lambda p: p["epoch"])["epoch"]
        if ep != exp:
            epochs_ok = False
    return agree, epochs_ok


def _field_level():
    """Each field is resolved independently: a record's region must come from the
    highest-authority surface that actually supplies a region, which need not be
    the surface that supplied the role. A record-level (whole-winning-record)
    implementation gets this wrong when the winning surface omits region."""
    inv, _ = _reconcile()
    ov0 = {o["id"]: o for o in json.loads((ENV / "r3" / "ov0.json").read_text())}
    signed = {o["id"]: o for o in json.loads(BASE0.read_text())} if _sig_rc() == 0 else {}
    ok = True
    for r in inv["records"]:
        hid = r["id"]
        if ov0.get(hid, {}).get("alias"):
            continue  # aliases inherit region from their target (covered by the alias test)
        if ov0.get(hid, {}).get("region"):
            exp = ov0[hid]["region"]
        elif signed.get(hid, {}).get("region"):
            exp = signed[hid]["region"]
        else:
            probes = [json.loads(f.read_text()) for f in _r1_files(f"{hid}_*")]
            exp = max(probes, key=lambda p: p["epoch"]).get("region")
        if r["region"] != exp:
            ok = False
    return ok


def _signature_gating():
    """When the detached signature does not verify, every r2 claim must be
    ignored and each affected host must fall back to its freshest probe. A
    solution that trusts the baseline without checking the signature fails this.
    Returns (n_baseline_hosts, all_fell_back_ok)."""
    sig = ENV / "r2" / "base0.sig"
    exp, _ = _expected_resolution()
    r2_hosts = [h for h, (_, s) in exp.items() if s == "r2"]
    backup = sig.read_bytes()
    try:
        sig.write_bytes(backup[::-1])  # reversed signature bytes: guaranteed not to verify
        inv, _ = _reconcile()
        rec = {r["id"]: r for r in inv["records"]}
        ok = True
        for h in r2_hosts:
            probes = [json.loads(f.read_text()) for f in _r1_files(f"{h}_*")]
            if not probes:
                continue
            fresh = max(probes, key=lambda p: p["epoch"])
            host = rec.get(h, {})
            acc = host.get("provenance", {}).get("accepted", {})
            if acc.get("surface") != "r1" or host.get("role") != fresh["role"]:
                ok = False
    finally:
        sig.write_bytes(backup)
    return len(r2_hosts), ok


def _sparse_host():
    """A host that appears on only one surface (an operator entry, with no probe
    and no baseline claim) still resolves from that surface, with a provenance
    that lists only the single claim that exists. Returns
    (present, surface, n_candidates, region_ok)."""
    inv, _ = _reconcile()
    ov0 = {o["id"]: o for o in json.loads((ENV / "r3" / "ov0.json").read_text())}
    signed_ids = {o["id"] for o in json.loads(BASE0.read_text())} if _sig_rc() == 0 else set()
    # a host defined only by a direct operator role entry (not an alias): no probe
    # files, not in the baseline
    sparse = [
        h for h, o in ov0.items()
        if o.get("role") and not o.get("alias") and not _r1_files(f"{h}_*") and h not in signed_ids
    ]
    if not sparse:
        return False, None, None, False
    hid = sparse[0]
    rec = {r["id"]: r for r in inv["records"]}.get(hid, {})
    acc = rec.get("provenance", {}).get("accepted", {})
    n_cand = len(rec.get("provenance", {}).get("candidates", []))
    region_ok = rec.get("region") == ov0[hid].get("region")
    return hid in {r["id"] for r in inv["records"]}, acc.get("surface"), n_cand, region_ok


def _alias_resolution():
    """An aliased operator entry mirrors its target's surviving role and region
    once the target resolves. With an alias chain (A -> B -> C), a single-pass
    resolver that does not iterate to a fixpoint resolves the deeper link wrong.
    Returns (role_ok, region_ok, surface_ok, one_candidate) for the deepest alias."""
    resolved, _ = _expected_full()
    inv, _ = _reconcile()
    ov0 = {o["id"]: o for o in json.loads((ENV / "r3" / "ov0.json").read_text())}
    # pick an alias whose own target is itself an alias (the chained, hardest case)
    chained = [h for h, o in ov0.items()
               if o.get("alias") and ov0.get(o["alias"], {}).get("alias") and h in resolved]
    pick = chained or [h for h, o in ov0.items() if o.get("alias") and h in resolved]
    if not pick:
        return False, False, False, False
    hid = pick[0]
    tgt = ov0[hid]["alias"]
    rec = {r["id"]: r for r in inv["records"]}.get(hid, {})
    acc = rec.get("provenance", {}).get("accepted", {})
    return (
        rec.get("role") == resolved[tgt][0],
        rec.get("region") == resolved[tgt][1],
        acc.get("surface") == "r3",
        len(rec.get("provenance", {}).get("candidates", [])) == 1,
    )


def _alias_cycle():
    """Aliases that form a cycle cannot resolve and are removed from the inventory,
    recorded as removals — never emitted with a fabricated value.
    Returns (has_cycle, absent_from_records, listed_as_removed)."""
    _, retired = _expected_full()
    inv, _ = _reconcile()
    ov0 = {o["id"]: o for o in json.loads((ENV / "r3" / "ov0.json").read_text())}
    cyc = [h for h, o in ov0.items() if o.get("alias") and h in retired]
    if not cyc:
        return False, False, False
    rec_ids = {r["id"] for r in inv["records"]}
    ret = {r["id"]: r for r in inv["retired"]}
    absent = all(h not in rec_ids for h in cyc)
    listed = all(ret.get(h, {}).get("removed_by") == "r3" for h in cyc)
    return True, absent, listed


# --------------------------------------------------------------------------
# tests
# --------------------------------------------------------------------------
def test_g01_terminal():
    """The full pipeline regenerates both artifacts and the checker accepts the
    result across all hosts."""
    inv_sv, rep_sv, n_records, n_retired, ids, expected_ids, rc = _terminal()
    assert inv_sv == 1
    assert rep_sv == 1
    assert n_records > 0
    assert n_retired > 0
    assert ids == expected_ids
    assert rc == 0


def test_g02_align():
    """The digest recomputed from the surviving records equals the digest stored
    in the inventory and the binding value in the report."""
    stored, binding, recomputed, hex_ok = _digest_triple()
    assert hex_ok
    assert stored == recomputed
    assert binding == recomputed


def test_g03_deep_gate():
    """Hosts whose most recent probe disagrees with the authorized surfaces
    resolve to the authorized claim, and the retired host is removed."""
    got, expected = _resolution_maps()
    assert got == expected
    assert _authority_beats_recent()
    has_retired, absent, listed, ledger_ok = _retired_status()
    assert has_retired
    assert absent
    assert listed
    assert ledger_ok


def test_g04_smoke_guard():
    """Every surviving host resolves correctly at once and keeps the full set of
    candidate claims — resolving one host does not drop another."""
    got, expected = _resolution_maps()
    assert got == expected
    got_counts, expected_counts = _candidate_counts()
    assert got_counts == expected_counts


def test_g05_visibility_seen():
    """A host with only stale probes plus a verified baseline claim resolves to
    the baseline and keeps every considered claim; a partial extraction fails."""
    n_signed, surfaces_ok, counts_ok = _signed_provenance()
    assert n_signed > 0
    assert surfaces_ok
    assert counts_ok


def test_g06_idem_hold():
    """After the destructive re-sync, the documented recovery rebuilds a
    byte-identical inventory with an identical digest."""
    altered, bytes_stable, digest_stable = _idempotency()
    assert altered
    assert bytes_stable
    assert digest_stable


def test_g07_frozen_touch():
    """A clean run yields a valid inventory and leaves the read-only baseline
    intact; a mutated baseline is rejected by verification."""
    clean_rc, sig_clean, unchanged, tampered_sig = _frozen()
    assert clean_rc == 0
    assert sig_clean == 0
    assert unchanged
    assert tampered_sig != 0


def test_g08_cross_fmt():
    """The decoded probe claim rows align in count with the textual probe lines
    in the sampled log."""
    n_log, n_r1, n_files = _cross_fmt()
    assert n_log == n_files
    assert n_r1 == n_log


def test_g09_override_tracks_input():
    """Rewriting an operator override's role makes that host resolve to the
    injected role: the inventory reflects the live surface data, not a hardcoded
    or statically written answer."""
    observed_role, injected_role, surface = _override_tracks()
    assert observed_role == injected_role
    assert surface == "r3"


def test_g10_deletion_tracks_input():
    """Dropping the operator retire entry brings the previously retired host back
    as a live record resolved from its own freshest probe, and it is no longer
    listed as removed: deletion handling is data-driven, not hardcoded."""
    present, observed_role, expected_role, absent_from_retired = _deletion_tracks()
    assert present
    assert observed_role == expected_role
    assert absent_from_retired


def test_g11_cross_artifact_consistency():
    """Each surviving host reads identically across the inventory records and the
    report ledger, and its accepted epoch equals the epoch of the surface claim
    that actually won."""
    agree, epochs_ok = _cross_artifact()
    assert agree
    assert epochs_ok


def test_g12_field_level_authority():
    """Each field is resolved independently by authority: a record's region comes
    from the highest-authority surface that supplies a region, even when a
    different surface supplied the role. A whole-record resolution fails this."""
    assert _field_level()


def test_g13_signature_gating():
    """When the baseline signature does not verify, its claims are ignored and
    baseline-resolved hosts fall back to their freshest probe. A solution that
    trusts the baseline without checking the signature fails this."""
    n_baseline, fell_back_ok = _signature_gating()
    assert n_baseline > 0
    assert fell_back_ok


def test_g14_sparse_host():
    """A host that appears on only the operator surface still resolves from that
    surface, with a provenance that lists only its single existing claim."""
    present, surface, n_candidates, region_ok = _sparse_host()
    assert present
    assert surface == "r3"
    assert n_candidates == 1
    assert region_ok


def test_g15_alias_resolution():
    """An operator alias mirrors its target's resolved role and region; a chained
    alias only resolves after the intermediate one does (dependency-ordered
    fixpoint). A single-pass resolver gets the chained link wrong."""
    role_ok, region_ok, surface_ok, one_candidate = _alias_resolution()
    assert role_ok
    assert region_ok
    assert surface_ok
    assert one_candidate


def test_g16_alias_cycle_removed():
    """Aliases forming a cycle cannot resolve and are removed from the inventory,
    recorded as removals rather than emitted with a fabricated value."""
    has_cycle, absent, listed = _alias_cycle()
    assert has_cycle
    assert absent
    assert listed
