"""Milestone 3: decode the scrambled container and re-import idempotently.

The container at this stage scrambles its numeric fields on top of the milestone 2
encoding, so qty and price come out wrong unless that layer is recovered too. On
the database side the import must converge on re-run (upsert), advance the identity
sequence, and honor the absent-cell preservation rule for text columns.
"""
from harness import psql, rand_seed, write_catalog, write_feed, run_import, assert_no_side_channel
import feedgen

M3_VERSION = 3


def _price(rec):
    return rec["price_ct"] / 100.0


class TestMilestone3:
    """Re-importing the same catalog converges instead of crashing on the
    primary key, drift in any column lands back in the row, the sequence advances,
    and an absent text cell preserves the existing value."""

    def test_clean_import_processes_50000_rows(self):
        psql("TRUNCATE products RESTART IDENTITY")
        write_catalog("/tmp/m3_full.bin", 50000, M3_VERSION, rand_seed())
        r = run_import(["/tmp/m3_full.bin"], timeout=240)
        assert r.returncode == 0, f"import exited {r.returncode}; {r.stderr[-500:]!r}"
        rc, c = psql("SELECT count(*) FROM products")
        assert c == "50000", f"count {c}, expected 50000"
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        assert last == "processed 50000 rows", f"final stdout line {last!r}"

    def test_second_run_against_same_feed_does_not_unique_key_violate(self):
        psql("TRUNCATE products RESTART IDENTITY")
        write_catalog("/tmp/m3_idem.bin", 20000, M3_VERSION, rand_seed())
        r = run_import(["/tmp/m3_idem.bin"], timeout=120)
        assert r.returncode == 0, f"first run exited {r.returncode}; {r.stderr[-400:]!r}"
        r = run_import(["/tmp/m3_idem.bin"], timeout=120)
        assert r.returncode == 0, (
            f"second run exited {r.returncode} (a primary-key collision is not "
            f"resolved as an upsert); {r.stderr[-400:]!r}"
        )
        rc, c = psql("SELECT count(*) FROM products")
        assert c == "20000", f"count {c} after second run, expected 20000"

    def _propagate(self, col, mutate_sql, expected, rid, recs):
        run_import(["/tmp/m3_prop.bin"], timeout=120)
        psql(mutate_sql)
        r = run_import(["/tmp/m3_prop.bin"], timeout=120)
        assert r.returncode == 0, f"re-import exited {r.returncode}; {r.stderr[-400:]!r}"
        rc, val = psql(f"SELECT {col} FROM products WHERE id = {rid}")
        return val

    def test_upsert_propagates_drift_in_every_column(self):
        seed = rand_seed()
        recs = write_catalog("/tmp/m3_prop.bin", 20000, M3_VERSION, seed)
        psql("TRUNCATE products RESTART IDENTITY")
        by_id = {r["id"]: r for r in recs}
        # qty
        rid = 1234
        rec = by_id[rid]
        val = self._propagate("qty", f"UPDATE products SET qty = -999 WHERE id = {rid}", rec["qty"], rid, recs)
        assert int(val) == rec["qty"], f"qty drift not restored: {val} != {rec['qty']}"
        # price
        rid = 5678
        rec = by_id[rid]
        val = self._propagate("price", f"UPDATE products SET price = 0.01 WHERE id = {rid}", _price(rec), rid, recs)
        assert abs(float(val) - _price(rec)) < 1e-9, f"price drift not restored: {val} != {_price(rec)}"
        # name (non-empty CSV value must overwrite a stale hot-fix)
        rid = 9012
        rec = by_id[rid]
        val = self._propagate("name", f"UPDATE products SET name = 'STALE-HOTFIX' WHERE id = {rid}", rec["name"], rid, recs)
        assert val == rec["name"], f"name drift not restored: {val!r} != {rec['name']!r}"
        # sku
        rid = 4567
        rec = by_id[rid]
        val = self._propagate("sku", f"UPDATE products SET sku = 'STALE-SKU' WHERE id = {rid}", rec["sku"], rid, recs)
        assert val == rec["sku"], f"sku drift not restored: {val!r} != {rec['sku']!r}"

    def test_post_import_sequence_advanced_to_max_id(self):
        psql("TRUNCATE products RESTART IDENTITY")
        write_catalog("/tmp/m3_seq.bin", 50000, M3_VERSION, rand_seed())
        r = run_import(["/tmp/m3_seq.bin"], timeout=240)
        assert r.returncode == 0, f"import exited {r.returncode}; {r.stderr[-400:]!r}"
        rc, new_id = psql(
            "WITH ins AS (INSERT INTO products (sku, name, qty, price) "
            "VALUES ('NEW-SKU', 'placeholder', 1, 1.0) RETURNING id) SELECT id FROM ins"
        )
        assert new_id == "50001", (
            f"operator INSERT after import returned id {new_id!r}, expected 50001; "
            "the identity sequence must be advanced to MAX(id) by the importer"
        )

    def test_absent_text_cell_preserves_existing_value(self):
        """An absent sku/name in a re-import preserves the existing Postgres
        value (operator hot-fix), while a present value overwrites it."""
        seed = rand_seed()
        recs = feedgen.gen_products(2000, seed)
        write_feed("/tmp/m3_ec_a.bin", recs, M3_VERSION)
        psql("TRUNCATE products RESTART IDENTITY")
        r = run_import(["/tmp/m3_ec_a.bin"], timeout=90)
        assert r.returncode == 0, f"initial import exited {r.returncode}; {r.stderr[-400:]!r}"
        # operator hot-fix on id=100, then a re-import where id=100 name is ABSENT
        psql("UPDATE products SET name = 'OPERATOR-HOTFIX' WHERE id = 100")
        recs2 = feedgen.gen_products(2000, seed)
        for r0 in recs2:
            if r0["id"] == 100:
                r0["name"] = None          # absent -> preserve
            if r0["id"] == 200:
                r0["name"] = "FRESH-NAME"  # present -> overwrite
        write_feed("/tmp/m3_ec_b.bin", recs2, M3_VERSION)
        r = run_import(["/tmp/m3_ec_b.bin"], timeout=90)
        assert r.returncode == 0, f"re-import exited {r.returncode}; {r.stderr[-400:]!r}"
        rc, n100 = psql("SELECT name FROM products WHERE id = 100")
        assert n100 == "OPERATOR-HOTFIX", (
            f"id=100 name is {n100!r}, expected the preserved hot-fix; an absent "
            "text cell must not clobber the existing value"
        )
        rc, n200 = psql("SELECT name FROM products WHERE id = 200")
        assert n200 == "FRESH-NAME", (
            f"id=200 name is {n200!r}, expected the present value to overwrite"
        )

    def test_importer_decodes_without_side_channel(self):
        assert_no_side_channel()
        write_catalog("/tmp/m3_sc.bin", 1000, M3_VERSION, rand_seed())
        r = run_import(["--dry-run", "/tmp/m3_sc.bin"], timeout=60)
        assert r.returncode == 0, f"decode failed with probe absent: {r.stderr[-400:]!r}"
