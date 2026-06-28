"""Milestone 4: decode the change-log container and fold it to final state.

The change-log container chains each record's masking off the previous record, so
decoding is strictly sequential and a single wrong record corrupts the rest. The
reconciliation is compared row for row against an independent reference computed
from the records the verifier generated (it never decodes the binary itself).
"""
from harness import psql, rand_seed, write_feed, run_import, assert_no_side_channel
import feedgen

FIELDS = ["sku", "name", "qty", "price_ct"]


def _reconcile(records):
    """Independent reference: version-order, tombstone-shadowed, field-level
    last-present merge, in a single pass."""
    max_del, max_put, best = {}, {}, {}
    for r in records:
        rid, ver = r["id"], r["version"]
        if r["op"] == "del":
            if ver > max_del.get(rid, 0):
                max_del[rid] = ver
        else:
            if ver > max_put.get(rid, 0):
                max_put[rid] = ver
            fb = best.setdefault(rid, {})
            for f in FIELDS:
                v = r.get(f)
                if v is not None and ver > (fb[f][0] if f in fb else 0):
                    fb[f] = (ver, v)
    out = {}
    for rid, mp in max_put.items():
        md = max_del.get(rid, 0)
        if mp <= md:
            continue
        fb = best.get(rid, {})
        row, ok = {}, True
        for f in FIELDS:
            if f not in fb or fb[f][0] <= md:
                ok = False
                break
            row[f] = fb[f][1]
        if ok:
            out[rid] = (row["sku"], row["name"], int(row["qty"]), round(row["price_ct"] / 100.0, 2))
    return out


def _db_state():
    rc, raw = psql("SELECT id, sku, name, qty, price FROM products ORDER BY id")
    out = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        i, sku, name, qty, price = line.split("|")
        out[int(i)] = (sku, name, int(qty), round(float(price), 2))
    return out


class TestMilestone4:
    """The change-log folds to the exact final state: tombstone shadowing,
    revive-after-del fresh, field-level last-present merge, del-as-final removal."""

    def test_changelog_reconciles_to_exact_final_state(self):
        for seed in (11, 47, 93):
            recs = feedgen.gen_changelog(2500, seed)
            write_feed(f"/tmp/m4_{seed}.bin", recs, 4)
            psql("TRUNCATE products RESTART IDENTITY")
            r = run_import(["--changelog", f"/tmp/m4_{seed}.bin"], timeout=120)
            assert r.returncode == 0, f"seed {seed} exited {r.returncode}; {r.stderr[-500:]!r}"
            want = _reconcile(recs)
            got = _db_state()
            assert got == want, (
                f"seed {seed}: reconciled table != reference "
                f"({len(got)} rows vs {len(want)} expected)"
            )

    def test_intricate_trap_battery(self):
        """Each id isolates one rule."""
        def R(i, v, op, sku=None, name=None, qty=None, pc=None):
            rec = {"id": i, "version": v, "op": op}
            if op != "del":
                rec.update(sku=sku, name=name, qty=qty, price_ct=pc)
            return rec
        recs = [
            R(1, 1, "put", "S1", "N1", 10, 200),
            R(2, 1, "put", "S2", "N2", 20, 300), R(2, 2, "del"), R(2, 3, "put", "S2b", "N2b", 21, 350),
            R(3, 1, "put", "S3", "N3", 30, 400), R(3, 2, "del"),
            R(4, 1, "put", "S4", "N4", 40, 500), R(4, 2, "del"), R(4, 3, "put", "S4b", "N4b", 41, 600),
            R(4, 4, "del"), R(4, 5, "put", "S4c", "N4c", 42, 700),
            R(5, 1, "put", "S5", "N5", 50, 800), R(5, 2, "put", None, None, 55, None),  # partial: only qty
        ]
        # shuffle deterministically
        order = [12, 0, 7, 3, 10, 1, 5, 9, 2, 11, 4, 8, 6]
        recs = [recs[i] for i in order]
        write_feed("/tmp/m4_traps.bin", recs, 4)
        psql("TRUNCATE products RESTART IDENTITY")
        r = run_import(["--changelog", "/tmp/m4_traps.bin"], timeout=60)
        assert r.returncode == 0, f"trap battery exited {r.returncode}; {r.stderr[-500:]!r}"
        want = _reconcile(recs)
        got = _db_state()
        assert 3 not in want, "reference bug: id 3 should be absent (latest op is del)"
        assert got == want, (
            f"trap battery: {got} != {want}. id2 revives fresh at v3, id3 is absent, "
            "id4 survives at v5 after two dels, id5 keeps v1 text with v2 qty"
        )

    def test_reconcile_streams_a_large_changelog_under_tight_heap(self):
        recs = feedgen.gen_changelog(55000, 424242)
        write_feed("/tmp/m4_big.bin", recs, 4)
        psql("TRUNCATE products RESTART IDENTITY")
        r = run_import(["--changelog", "/tmp/m4_big.bin"], timeout=180, heap_mb=64)
        assert r.returncode == 0, (
            f"large change-log exited {r.returncode} under a 64 MB heap; it must "
            f"reconcile in a single streaming pass.\nstderr: {r.stderr[-500:]!r}"
        )
        want = _reconcile(recs)
        got = _db_state()
        assert got == want, f"large reconcile != reference ({len(got)} vs {len(want)})"

    def test_reconcile_decodes_without_side_channel(self):
        assert_no_side_channel()
        recs = feedgen.gen_changelog(500, rand_seed())
        write_feed("/tmp/m4_sc.bin", recs, 4)
        psql("TRUNCATE products RESTART IDENTITY")
        r = run_import(["--changelog", "/tmp/m4_sc.bin"], timeout=60)
        assert r.returncode == 0, f"reconcile failed with probe absent: {r.stderr[-400:]!r}"
