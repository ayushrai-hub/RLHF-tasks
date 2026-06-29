"""Milestone 2: decode the upgraded container, stream it under a tight heap, and
honor the resume-from-checkpoint contract.

The container at this stage uses a deeper encoding than milestone 1, so a decoder
that only handled the milestone 1 feed no longer reads it. The single
asymmetric-scoring lever is test_resume_contract_binary_and: three orthogonal
sub-contracts in one test, all of which must be right at once.
"""
import re
import secrets
import subprocess
from pathlib import Path

from harness import (psql, rand_seed, write_catalog, write_feed, run_import,
                     assert_no_side_channel)
import feedgen

CHECKPOINT = Path("/var/lib/csv-importer/.checkpoint")
M2_VERSION = 2


def _price(rec) -> str:
    return f"{rec['price_ct'] / 100:.2f}"


def _count() -> int:
    rc, n = psql("SELECT count(*) FROM products")
    assert n.isdigit(), f"count query failed: {n!r}"
    return int(n)


def _write_checkpoint(value: str) -> None:
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT.write_text(value)


def _agent_src() -> str:
    parts = []
    paths = [Path("/app/import.js")]
    lib = Path("/app/lib")
    if lib.is_dir():
        paths += sorted(lib.rglob("*.js"))
    for p in paths:
        try:
            parts.append(p.read_text())
        except OSError:
            pass
    return "\n".join(parts)


class TestMilestone2:
    """The full catalog must decode and stream under --max-old-space-size=64, and
    the importer must honor the resume-from-checkpoint contract."""

    def test_full_dry_run_under_tight_heap(self) -> None:
        """Decoding 200k records under a 64 MB heap requires yielding records
        lazily; a decoder that collects every record into an array first OOMs."""
        CHECKPOINT.unlink(missing_ok=True)
        write_catalog("/tmp/m2_full.bin", 200000, M2_VERSION, rand_seed())
        r = run_import(["--dry-run", "/tmp/m2_full.bin"], timeout=120, heap_mb=64)
        assert r.returncode == 0, (
            f"--dry-run exited {r.returncode} under a 64 MB heap; stderr: {r.stderr[-600:]!r}"
        )
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        assert last == "processed 200000 rows", f"final stdout line {last!r}"

    def test_dry_run_reports_actual_count(self) -> None:
        """Anti-cheat: a randomized record count, so a hardcoded total fails."""
        n = 30000 + secrets.randbelow(40001)
        write_catalog("/tmp/m2_rand.bin", n, M2_VERSION, rand_seed())
        r = run_import(["--dry-run", "/tmp/m2_rand.bin"], timeout=90, heap_mb=192)
        assert r.returncode == 0, f"--dry-run exited {r.returncode}; stderr: {r.stderr[-600:]!r}"
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        assert last == f"processed {n} rows", f"final stdout line {last!r}, expected {n}"

    def test_resume_contract_binary_and(self) -> None:
        """Binary AND across the three resume contracts (all must hold at once):

          (1) no flag + poisoned checkpoint -> full import.
          (2) --resume-from auto + checkpoint id:5000 -> exclusive: ids 5001..20000.
          (3) --resume-from id:15000 + checkpoint id:5000 -> literal wins and is
              inclusive: ids 15000..20000.
        """
        write_catalog("/tmp/m2_resume.bin", 20000, M2_VERSION, rand_seed())

        psql("TRUNCATE products RESTART IDENTITY")
        _write_checkpoint("id:10000")
        r = run_import(["/tmp/m2_resume.bin"], timeout=120)
        assert r.returncode == 0, f"(1) exited {r.returncode}; {r.stderr[-400:]!r}"
        assert _count() == 20000, (
            f"(1) no-flag with a poisoned checkpoint imported {_count()} rows, "
            "expected 20000; an import without --resume-from ignores the checkpoint"
        )

        psql("TRUNCATE products RESTART IDENTITY")
        _write_checkpoint("id:5000")
        r = run_import(["--resume-from", "auto", "/tmp/m2_resume.bin"], timeout=120)
        assert r.returncode == 0, f"(2) exited {r.returncode}; {r.stderr[-400:]!r}"
        assert _count() == 15000, (
            f"(2) --resume-from auto + checkpoint id:5000 imported {_count()}, "
            "expected 15000 (ids 5001..20000; auto is exclusive of the recorded id)"
        )

        psql("TRUNCATE products RESTART IDENTITY")
        _write_checkpoint("id:5000")
        r = run_import(["--resume-from", "id:15000", "/tmp/m2_resume.bin"], timeout=120)
        assert r.returncode == 0, f"(3) exited {r.returncode}; {r.stderr[-400:]!r}"
        assert _count() == 5001, (
            f"(3) --resume-from id:15000 (checkpoint id:5000) imported {_count()}, "
            "expected 5001 (ids 15000..20000; literal wins and is inclusive)"
        )

    def test_skip_counts_decoded_records_by_id(self) -> None:
        """The skip target is matched against decoded record ids, not byte or
        record offsets, so a checkpoint of id:5 keeps only ids 6..10."""
        write_catalog("/tmp/m2_skip.bin", 10, M2_VERSION, rand_seed())
        psql("TRUNCATE products RESTART IDENTITY")
        _write_checkpoint("id:5")
        r = run_import(["--resume-from", "auto", "/tmp/m2_skip.bin"], timeout=60)
        assert r.returncode == 0, f"skip exited {r.returncode}; {r.stderr[-400:]!r}"
        assert _count() == 5, f"skip-after-id:5 on 10 records imported {_count()}, expected 5"

    def test_options_pinner_supervisor_is_stopped(self) -> None:
        """After a 12-second window (more than two watchdog ticks) neither the
        pinner nor its watchdog may be running; otherwise the pinner keeps
        stomping the checkpoint back to its baseline."""
        import time as _time
        _time.sleep(12)
        wd = subprocess.run(["pgrep", "-f", "options-pinner-watchdog"], capture_output=True, text=True)
        assert wd.returncode != 0, (
            f"options-pinner-watchdog still running (pid {wd.stdout.strip()!r}); "
            "kill the watchdog first, then the pinner"
        )
        pin = subprocess.run(["pgrep", "-f", r"/usr/local/bin/options-pinner$"], capture_output=True, text=True)
        assert pin.returncode != 0, (
            f"options-pinner still running (pid {pin.stdout.strip()!r}) after 12s; "
            "the watchdog respawns it unless the watchdog is also stopped"
        )

    def test_checkpoint_format_canonical_after_full_import(self) -> None:
        """After a clean import the checkpoint is id:<integer> naming the last
        committed id."""
        write_catalog("/tmp/m2_ckpt.bin", 20000, M2_VERSION, rand_seed())
        psql("TRUNCATE products RESTART IDENTITY")
        CHECKPOINT.unlink(missing_ok=True)
        r = run_import(["/tmp/m2_ckpt.bin"], timeout=120)
        assert r.returncode == 0, f"import exited {r.returncode}; {r.stderr[-400:]!r}"
        assert CHECKPOINT.exists(), "checkpoint was never written"
        raw = CHECKPOINT.read_text().strip()
        assert re.fullmatch(r"id:\d+", raw), f"checkpoint {raw!r} is not id:<integer>"
        rc, mx = psql("SELECT max(id) FROM products")
        assert int(raw.split(":", 1)[1]) == int(mx), (
            f"checkpoint {raw!r} does not match max committed id {mx}"
        )

    def test_checkpoint_never_names_uncommitted_rows_under_failed_batch(self) -> None:
        """If a batch INSERT fails (a duplicate id forces a primary-key
        violation), the checkpoint must not name rows beyond the last committed
        id; a write-before-commit implementation records the failing batch."""
        recs = feedgen.gen_products(2000, rand_seed())
        recs[1499]["id"] = 3  # force a duplicate id mid-stream
        write_feed("/tmp/m2_dup.bin", recs, M2_VERSION)
        psql("TRUNCATE products RESTART IDENTITY")
        CHECKPOINT.unlink(missing_ok=True)
        run_import(["/tmp/m2_dup.bin"], timeout=90, heap_mb=192)
        rc, mx = psql("SELECT COALESCE(max(id), 0) FROM products")
        max_committed = int(mx)
        if CHECKPOINT.exists():
            raw = CHECKPOINT.read_text().strip()
            m = re.fullmatch(r"id:(\d+)", raw)
            assert m is not None, f"checkpoint {raw!r} is not id:<integer> after a failed import"
            assert int(m.group(1)) <= max_committed, (
                f"checkpoint names id:{m.group(1)} but Postgres committed only up to "
                f"id:{max_committed}; write the checkpoint after each batch commit, never before"
            )

    def test_specific_rows_match_decoded_feed(self) -> None:
        """Spot-check decoded field values in Postgres after a full milestone-2
        import, so a decoder that extracts ids correctly (enough for the resume
        logic) but writes garbage or unconverted sku/name/qty/price fails. The
        price_ct/100 two-decimal conversion is checked explicitly."""
        seed = rand_seed()
        recs = write_catalog("/tmp/m2_spot.bin", 4000, M2_VERSION, seed)
        psql("TRUNCATE products RESTART IDENTITY")
        CHECKPOINT.unlink(missing_ok=True)
        r = run_import(["/tmp/m2_spot.bin"], timeout=120)
        assert r.returncode == 0, f"import exited {r.returncode}; {r.stderr[-600:]!r}"
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
            assert price == _price(rec), (
                f"id={rid} price {price} != decoded {_price(rec)} (price_ct/100, two decimals)"
            )

    def test_importer_decodes_without_side_channel(self) -> None:
        """The importer decodes the upgraded feed itself, with no shell-out to the
        reference probe or another interpreter."""
        assert_no_side_channel()
        write_catalog("/tmp/m2_sc.bin", 1000, M2_VERSION, rand_seed())
        r = run_import(["--dry-run", "/tmp/m2_sc.bin"], timeout=60)
        assert r.returncode == 0, f"decode failed with probe absent: {r.stderr[-400:]!r}"
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        assert last == "processed 1000 rows", f"final stdout line {last!r}"
