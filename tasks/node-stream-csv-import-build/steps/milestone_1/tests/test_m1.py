"""Milestone 1: decode the catalog container and land every record in postgres."""
import secrets

from harness import psql, rand_seed, write_catalog, run_import, assert_no_side_channel


def _price(rec):
    return f"{rec['price_ct'] / 100:.2f}"


class TestMilestone1:
    """The importer must reverse-engineer the catalog container and write every
    decoded record, with every column, into public.products."""

    def test_dry_run_reports_decoded_record_count(self) -> None:
        """--dry-run decodes the container and prints 'processed <N> rows'.

        N is randomized per run, so a hardcoded count or a parser that does not
        actually decode the container fails.
        """
        n = 10 + secrets.randbelow(21)  # 10..30
        seed = rand_seed()
        write_catalog("/tmp/m1_sample.bin", n, 1, seed)
        r = run_import(["--dry-run", "/tmp/m1_sample.bin"], timeout=60)
        assert r.returncode == 0, (
            f"import.js --dry-run exited {r.returncode}.\nstdout: {r.stdout!r}\n"
            f"stderr: {r.stderr[-600:]!r}"
        )
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        assert last == f"processed {n} rows", (
            f"final stdout line is {last!r}, expected 'processed {n} rows'"
        )

    def test_import_completes_and_count_matches(self) -> None:
        """TRUNCATE, import a 50k-record container, count(*) == 50000."""
        rc, _ = psql("TRUNCATE products")
        assert rc == 0, "TRUNCATE failed before import"
        seed = rand_seed()
        write_catalog("/tmp/m1_catalog.bin", 50000, 1, seed)
        r = run_import(["/tmp/m1_catalog.bin"], timeout=240)
        assert r.returncode == 0, f"import exited {r.returncode}.\nstderr: {r.stderr[-600:]!r}"
        rc, c = psql("SELECT count(*) FROM products")
        assert c == "50000", f"products has {c} rows after import, expected 50000"

    def test_every_row_has_non_null_qty(self) -> None:
        """No decoded qty may be lost on the way to the INSERT."""
        rc, c = psql("SELECT count(*) FROM products WHERE qty IS NULL")
        assert c == "0", f"{c} rows have qty IS NULL; a column is being dropped"

    def test_specific_rows_match_decoded_feed(self) -> None:
        """Spot-check rows against the exact records the verifier encoded, so a
        solution that fabricates rows instead of decoding the feed fails."""
        seed = rand_seed()
        recs = write_catalog("/tmp/m1_spot.bin", 4000, 1, seed)
        rc, _ = psql("TRUNCATE products")
        r = run_import(["/tmp/m1_spot.bin"], timeout=120)
        assert r.returncode == 0, f"import exited {r.returncode}.\nstderr: {r.stderr[-600:]!r}"
        by_id = {rec["id"]: rec for rec in recs}
        for rid in (1, 37, 1999, 4000):
            rec = by_id[rid]
            rc, val = psql(
                f"SELECT sku || '|' || name || '|' || qty || '|' || price "
                f"FROM products WHERE id = {rid}"
            )
            assert val, f"no row id={rid}; import incomplete"
            sku, name, qty, price = val.split("|")
            assert sku == rec["sku"], f"id={rid} sku {sku!r} != decoded {rec['sku']!r}"
            assert name == rec["name"], f"id={rid} name {name!r} != decoded {rec['name']!r}"
            assert int(qty) == rec["qty"], f"id={rid} qty {qty} != decoded {rec['qty']}"
            assert price == _price(rec), f"id={rid} price {price} != decoded {_price(rec)}"

    def test_importer_decodes_without_the_probe(self) -> None:
        """The graded import runs with the reference probe moved aside, and the
        importer source must not shell out to it or another interpreter."""
        assert_no_side_channel()
        seed = rand_seed()
        write_catalog("/tmp/m1_noprobe.bin", 500, 1, seed)
        r = run_import(["--dry-run", "/tmp/m1_noprobe.bin"], timeout=60)
        assert r.returncode == 0, (
            f"import failed with the probe absent ({r.returncode}); it must decode "
            f"the feed itself.\nstderr: {r.stderr[-600:]!r}"
        )
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        assert last == "processed 500 rows", f"final stdout line {last!r}"
