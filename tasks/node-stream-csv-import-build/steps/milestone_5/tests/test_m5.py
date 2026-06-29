"""Milestone 5: concurrent imports must claim the feed atomically.

A fleet of importers launched under one feed-key must resolve to exactly one
importer that does the work plus one ledger row; the rest exit 0 reporting they
imported nothing. A check-then-act race either crashes on the import_runs primary
key or runs the import more than once, and is caught here over many rounds.
"""
import secrets
import subprocess

from harness import (
    psql, rand_seed, write_catalog, probe_stashed, assert_no_side_channel,
)

IMPORT = "/app/import.js"


def _price(rec):
    return f"{rec['price_ct'] / 100:.2f}"


def _spot_check(recs, n):
    """Verify a few decoded rows match the records the verifier encoded, so a
    fleet that reads the plaintext header count and inserts fabricated rows
    instead of decoding the feed fails."""
    by_id = {rec["id"]: rec for rec in recs}
    for rid in (1, n // 2, n):
        rec = by_id[rid]
        _, val = psql(
            f"SELECT sku || '|' || name || '|' || qty || '|' || price "
            f"FROM products WHERE id = {rid}"
        )
        assert val, f"no row id={rid}; the feed was not decoded and imported"
        sku, name, qty, price = val.split("|")
        assert sku == rec["sku"], f"id={rid} sku {sku!r} != decoded {rec['sku']!r}"
        assert name == rec["name"], f"id={rid} name {name!r} != decoded {rec['name']!r}"
        assert int(qty) == rec["qty"], f"id={rid} qty {qty} != decoded {rec['qty']}"
        assert price == _price(rec), f"id={rid} price {price} != decoded {_price(rec)}"


def _run_fleet(feed, feed_key, n):
    """Launch n concurrent importers for one feed-key; return (rc, last_line, stderr) each."""
    with probe_stashed():
        procs = [
            subprocess.Popen(
                ["node", IMPORT, "--feed-key", feed_key, feed],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            for _ in range(n)
        ]
        out = []
        for p in procs:
            so, se = p.communicate(timeout=120)
            last = so.strip().splitlines()[-1] if so.strip() else ""
            out.append((p.returncode, last, se))
    return out


class TestMilestone5:
    """Concurrent imports under one feed-key must claim it atomically: exactly one
    importer does the work and records the run, the rest skip."""

    def test_concurrent_imports_claim_atomically(self) -> None:
        """Over many rounds a fleet under one feed-key yields exactly one worker
        and one finished ledger row, every process exits 0, and products holds the
        decoded set."""
        n_procs = 6
        rounds = 12
        for r in range(rounds):
            seed = rand_seed()
            n = 1500 + secrets.randbelow(500)
            recs = write_catalog("/tmp/m5_feed.bin", n, 1, seed)
            key = f"feed-{r}-{secrets.token_hex(4)}"
            psql("TRUNCATE products")
            psql(f"DELETE FROM import_runs WHERE feed_key = '{key}'")
            results = _run_fleet("/tmp/m5_feed.bin", key, n_procs)
            for rc, last, se in results:
                assert rc == 0, (
                    f"round {r}: a concurrent importer exited {rc}; "
                    f"stderr {se[-300:]!r}"
                )
            stdouts = [x[1] for x in results]
            winners = [x for x in results if x[1] == f"processed {n} rows"]
            losers = [x for x in results if x[1] == "processed 0 rows"]
            assert len(winners) == 1, (
                f"round {r}: expected exactly 1 importer to do the work, "
                f"got {len(winners)} (stdout last lines {stdouts})"
            )
            assert len(losers) == n_procs - 1, (
                f"round {r}: expected {n_procs - 1} importers to skip, "
                f"got {len(losers)} (stdout last lines {stdouts})"
            )
            _, rows = psql(
                f"SELECT row_count FROM import_runs WHERE feed_key = '{key}' AND finished"
            )
            assert rows == str(n), (
                f"round {r}: import_runs has finished row_count {rows!r}, expected {n}"
            )
            _, c = psql("SELECT count(*) FROM products")
            assert c == str(n), f"round {r}: products has {c} rows, expected {n}"
            _spot_check(recs, n)

    def test_importer_decodes_without_the_probe(self) -> None:
        """The graded run has the reference probe moved aside; the importer must
        decode the feed itself and not shell out to it."""
        assert_no_side_channel()
        seed = rand_seed()
        n = 800
        recs = write_catalog("/tmp/m5_noprobe.bin", n, 1, seed)
        key = f"noprobe-{secrets.token_hex(4)}"
        psql(f"DELETE FROM import_runs WHERE feed_key = '{key}'")
        psql("TRUNCATE products")
        results = _run_fleet("/tmp/m5_noprobe.bin", key, 2)
        for rc, last, se in results:
            assert rc == 0, f"importer exited {rc} with probe absent; stderr {se[-300:]!r}"
        winners = [x for x in results if x[1] == f"processed {n} rows"]
        assert len(winners) == 1, (
            f"expected exactly 1 winner with the probe absent, got {len(winners)} "
            f"(stdout last lines {[x[1] for x in results]})"
        )
        _, c = psql("SELECT count(*) FROM products")
        assert c == str(n), f"products has {c} rows with probe absent, expected {n}"
        _spot_check(recs, n)
