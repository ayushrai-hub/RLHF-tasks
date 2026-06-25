import csv
import json
import os
import shutil
import subprocess
from pathlib import Path

APP = Path(os.environ.get("TASK_ENV_DIR", "/app/environment"))
BIN = APP / "bin" / "ostore"
OUTPUT_NAMES = ["manifest.json", "checksum-report.tsv", "provenance.json"]


def run_cmd(args, *, cwd=APP, check=True):
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"command failed: {' '.join(map(str, args))}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def build_cli():
    run_cmd(["make", "build"])
    assert BIN.exists(), "the /app/environment/bin/ostore entrypoint must be built"
    if APP == Path("/app/environment"):
        subprocess.run(["/app/environment/bin/ostore", "--help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    else:
        subprocess.run([str(BIN), "--help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)


def sha(data: bytes) -> str:
    result = subprocess.run(["sha256sum"], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return result.stdout.decode().split()[0]


def canonical_row(batch_id: str, obj: dict) -> str:
    return f"{batch_id}\t{obj['logical_key']}\t{obj['relative_path']}\t{obj['size']}\t{obj['sha256']}\n"


def rows_digest(rows: list[str]) -> str:
    return sha("".join(rows).encode())


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def read_report(path: Path) -> list[dict]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def write_batch(root: Path, batch_id: str, phase: str, epoch: int, objects: dict[str, bytes], *, sidecar_overrides=None):
    sidecar_overrides = sidecar_overrides or {}
    receipt_objects = []
    for logical_key in sorted(objects):
        data = objects[logical_key]
        rel = f"objects/{batch_id}/{logical_key}.dat"
        payload = root / rel
        payload.parent.mkdir(parents=True, exist_ok=True)
        payload.write_bytes(data)
        digest = sha(data)
        sidecar_digest = sidecar_overrides.get(logical_key, digest)
        Path(str(payload) + ".sha256").write_text(f"{sidecar_digest}  {rel}\n")
        receipt_objects.append(
            {
                "logical_key": logical_key,
                "relative_path": rel,
                "size": len(data),
                "sha256": digest,
            }
        )
    receipts_dir = root / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema_version": 1,
        "batch_id": batch_id,
        "phase": phase,
        "epoch": epoch,
        "objects": receipt_objects,
    }
    (receipts_dir / f"{batch_id}.receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


def write_manual_receipt(root: Path, batch_id: str, receipt: dict):
    d = root / "receipts"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{batch_id}.receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


def object_spec(
    root: Path,
    batch_id: str,
    logical_key: str,
    data: bytes,
    *,
    relative_path: str | None = None,
    receipt_size: int | None = None,
    receipt_sha: str | None = None,
    sidecar_digest: str | None = None,
    write_payload: bool = True,
    write_sidecar: bool = True,
) -> dict:
    rel = relative_path or f"objects/{batch_id}/{logical_key}.dat"
    payload = root / rel
    digest = sha(data)
    if write_payload:
        payload.parent.mkdir(parents=True, exist_ok=True)
        payload.write_bytes(data)
    if write_sidecar:
        payload.parent.mkdir(parents=True, exist_ok=True)
        Path(str(payload) + ".sha256").write_text(f"{sidecar_digest or digest}  {rel}\n")
    return {
        "logical_key": logical_key,
        "relative_path": rel,
        "size": len(data) if receipt_size is None else receipt_size,
        "sha256": digest if receipt_sha is None else receipt_sha,
    }


def seed_stale_outputs(out: Path) -> dict[str, bytes]:
    out.mkdir(parents=True, exist_ok=True)
    stale = {
        "manifest.json": b"stale manifest\n",
        "checksum-report.tsv": b"stale report\n",
        "provenance.json": b"stale provenance\n",
    }
    for name, data in stale.items():
        (out / name).write_bytes(data)
    return stale


def assert_outputs_unchanged(out: Path, stale: dict[str, bytes]):
    for name, data in stale.items():
        assert (out / name).read_bytes() == data


def assert_rebuild_fails_without_output_change(store: Path, out: Path):
    stale = seed_stale_outputs(out)
    result = run_cmd([str(BIN), "rebuild", "--store", str(store), "--out", str(out)], check=False)
    assert result.returncode != 0
    assert_outputs_unchanged(out, stale)


def assert_bundle_matches_store(store: Path, out: Path):
    rows = committed_objects_from_receipts(store)
    manifest = read_json(out / "manifest.json")
    report_rows = read_report(out / "checksum-report.tsv")
    assert_manifest_matches_rows(manifest, rows)
    assert_report_matches_rows(report_rows, rows)
    assert_provenance(out, manifest, rows)


def receipt_phase_sets(root: Path):
    committed = set()
    non_committed = set()
    for receipt_path in sorted((root / "receipts").glob("*.receipt.json")):
        receipt = json.loads(receipt_path.read_text())
        if receipt.get("phase") == "committed":
            committed.add(receipt["batch_id"])
        else:
            non_committed.add(receipt["batch_id"])
    return committed, non_committed


def committed_objects_from_receipts(root: Path):
    rows = []
    for receipt_path in sorted((root / "receipts").glob("*.receipt.json")):
        receipt = json.loads(receipt_path.read_text())
        if receipt.get("phase") != "committed":
            continue
        batch_id = receipt["batch_id"]
        for obj in sorted(receipt["objects"], key=lambda item: item["logical_key"]):
            payload = root / obj["relative_path"]
            sidecar = Path(str(payload) + ".sha256")
            sidecar_digest = sidecar.read_text().split()[0].lower()
            rows.append(
                {
                    "batch_id": batch_id,
                    "epoch": receipt["epoch"],
                    "logical_key": obj["logical_key"],
                    "relative_path": obj["relative_path"],
                    "size": obj["size"],
                    "sha256": obj["sha256"],
                    "sidecar_sha256": sidecar_digest,
                }
            )
    return sorted(rows, key=lambda row: (row["batch_id"], row["logical_key"]))


def assert_manifest_matches_rows(manifest: dict, rows: list[dict]):
    assert manifest["schema_version"] == 1
    assert manifest["store"] == "offline-object-store"
    assert manifest["generated_by"] == "ostore-manifest-v1"
    assert manifest["object_count"] == len(rows)
    expected_batches = sorted({row["batch_id"] for row in rows})
    assert [batch["batch_id"] for batch in manifest["batches"]] == expected_batches
    assert manifest["commit_count"] == len(expected_batches)

    all_canonical = []
    by_batch = {batch_id: [] for batch_id in expected_batches}
    for row in rows:
        by_batch[row["batch_id"]].append(row)
    for batch in manifest["batches"]:
        batch_rows = by_batch[batch["batch_id"]]
        assert batch["epoch"] == batch_rows[0]["epoch"]
        assert batch["object_count"] == len(batch_rows)
        objects = batch["objects"]
        assert [obj["logical_key"] for obj in objects] == [row["logical_key"] for row in batch_rows]
        for obj, row in zip(objects, batch_rows):
            assert obj == {
                "logical_key": row["logical_key"],
                "relative_path": row["relative_path"],
                "size": row["size"],
                "sha256": row["sha256"],
            }
            all_canonical.append(canonical_row(batch["batch_id"], obj))
        assert batch["batch_sha256"] == rows_digest([canonical_row(batch["batch_id"], obj) for obj in objects])
    assert manifest["content_root"] == rows_digest(all_canonical)


def assert_report_matches_rows(report_rows: list[dict], rows: list[dict]):
    normalized = []
    for row in report_rows:
        normalized.append(
            {
                "batch_id": row["batch_id"],
                "logical_key": row["logical_key"],
                "relative_path": row["relative_path"],
                "size": int(row["size"]),
                "sha256": row["sha256"],
                "sidecar_sha256": row["sidecar_sha256"],
            }
        )
    expected = [
        {
            "batch_id": row["batch_id"],
            "logical_key": row["logical_key"],
            "relative_path": row["relative_path"],
            "size": row["size"],
            "sha256": row["sha256"],
            "sidecar_sha256": row["sidecar_sha256"],
        }
        for row in rows
    ]
    assert normalized == expected


def assert_provenance(out: Path, manifest: dict, rows: list[dict]):
    prov_path = out / "provenance.json"
    prov = read_json(prov_path)
    assert set(prov) == {
        "schema_version",
        "generated_by",
        "input_digest",
        "manifest_sha256",
        "checksum_report_sha256",
        "commit_count",
        "object_count",
        "content_root",
    }
    assert prov["schema_version"] == 1
    assert prov["generated_by"] == "ostore-manifest-v1"
    assert prov["commit_count"] == manifest["commit_count"]
    assert prov["object_count"] == manifest["object_count"]
    assert prov["content_root"] == manifest["content_root"]
    assert prov["manifest_sha256"] == sha((out / "manifest.json").read_bytes())
    assert prov["checksum_report_sha256"] == sha((out / "checksum-report.tsv").read_bytes())
    input_rows = [
        f"{row['batch_id']}\t{row['logical_key']}\t{row['relative_path']}\t{row['sha256']}\t{row['sidecar_sha256']}\n"
        for row in rows
    ]
    assert prov["input_digest"] == rows_digest(sorted(input_rows))


class TestObjectStoreManifestAtomicity:
    def test_crash_retry_fixture_publishes_only_committed_batches(self, tmp_path):
        """The bundled replay leaves a full prepared batch on disk, but only committed receipt batches are publishable."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        run_cmd([str(BIN), "fixture", "--scenario", "crash-retry", "--store", str(store)])
        run_cmd([str(BIN), "rebuild", "--store", str(store), "--out", str(out)])

        rows = committed_objects_from_receipts(store)
        manifest = read_json(out / "manifest.json")
        report_rows = read_report(out / "checksum-report.tsv")

        committed_ids, non_committed_ids = receipt_phase_sets(store)
        assert non_committed_ids, "the replay fixture must exercise a non-committed batch"
        assert {batch["batch_id"] for batch in manifest["batches"]} == committed_ids
        manifest_text = json.dumps(manifest)
        for batch_id in non_committed_ids:
            assert batch_id not in manifest_text
        assert_manifest_matches_rows(manifest, rows)
        assert_report_matches_rows(report_rows, rows)
        assert_provenance(out, manifest, rows)

    def test_rebuild_outputs_are_reproducible_and_have_no_runtime_stamp_fields(self, tmp_path):
        """Rerunning rebuild on the same store must produce byte-identical manifest, report, and provenance artifacts."""
        build_cli()
        store = tmp_path / "store"
        out1 = tmp_path / f"out{1}"
        out2 = tmp_path / f"out{2}"
        run_cmd([str(BIN), "fixture", "--scenario", "clean-basic", "--store", str(store)])
        run_cmd([str(BIN), "rebuild", "--store", str(store), "--out", str(out1)])
        run_cmd([str(BIN), "rebuild", "--store", str(store), "--out", str(out2)])

        for name in ["manifest.json", "checksum-report.tsv", "provenance.json"]:
            assert (out1 / name).read_bytes() == (out2 / name).read_bytes()
        provenance = read_json(out1 / "provenance.json")
        assert "generated_at" not in provenance
        assert "hostname" not in provenance

    def test_heldout_full_prepared_folder_is_excluded_after_retry(self, tmp_path):
        """Directory contents alone are insufficient: a complete prepared batch must lose to the committed rerun."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        write_batch(
            store,
            "audit-" + f"{10:03d}" + "-prepared",
            "prepared",
            501,
            {
                "ledger/a": b"partial-a\n",
                "ledger/b": b"partial-b\n",
            },
        )
        write_batch(
            store,
            "audit-" + f"{11:03d}" + "-rerun",
            "committed",
            502,
            {
                "ledger/a": b"committed-a\n",
                "ledger/b": b"committed-b\n",
                "ledger/c": b"committed-c\n",
            },
        )
        run_cmd([str(BIN), "rebuild", "--store", str(store), "--out", str(out)])
        rows = committed_objects_from_receipts(store)
        manifest = read_json(out / "manifest.json")
        committed_ids, non_committed_ids = receipt_phase_sets(store)
        assert {batch["batch_id"] for batch in manifest["batches"]} == committed_ids
        report_text = (out / "checksum-report.tsv").read_text()
        for batch_id in non_committed_ids:
            assert batch_id not in report_text
        assert_manifest_matches_rows(manifest, rows)

    def test_checksum_sidecar_mismatch_rejects_without_replacing_existing_outputs(self, tmp_path):
        """A committed receipt whose sidecar disagrees with the payload is an error and must not clobber prior outputs."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        out.mkdir()
        stale = {
            "manifest.json": b"stale manifest\n",
            "checksum-report.tsv": b"stale report\n",
            "provenance.json": b"stale provenance\n",
        }
        for name, data in stale.items():
            (out / name).write_bytes(data)
        write_batch(
            store,
            "checksum-a",
            "committed",
            701,
            {"events/a": b"payload-a\n"},
            sidecar_overrides={"events/a": "0" * 64},
        )
        result = run_cmd([str(BIN), "rebuild", "--store", str(store), "--out", str(out)], check=False)
        assert result.returncode != 0
        for name, data in stale.items():
            assert (out / name).read_bytes() == data

    def test_public_digest_formulas_and_report_schema_hold_for_nested_keys(self, tmp_path):
        """The manifest hashes, TSV rows, and provenance hashes must follow the documented canonical formulas."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        write_batch(
            store,
            "zeta-b",
            "committed",
            22,
            {"regions/eu/west": b"eu-west\n", "regions/us/east": b"us-east\n"},
        )
        write_batch(
            store,
            "alpha-a",
            "committed",
            21,
            {"root": b"root-object\n"},
        )
        run_cmd([str(BIN), "rebuild", "--store", str(store), "--out", str(out)])
        rows = committed_objects_from_receipts(store)
        manifest = read_json(out / "manifest.json")
        report_rows = read_report(out / "checksum-report.tsv")
        assert_manifest_matches_rows(manifest, rows)
        assert_report_matches_rows(report_rows, rows)
        assert_provenance(out, manifest, rows)

    def test_empty_publishable_set_has_empty_manifest_and_header_only_report(self, tmp_path):
        """A store with only non-committed receipts rebuilds to an empty committed manifest, not to a directory listing."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        write_batch(store, "only-prepared", "prepared", 1, {"tmp/a": b"payload\n"})
        run_cmd([str(BIN), "rebuild", "--store", str(store), "--out", str(out)])
        manifest = read_json(out / "manifest.json")
        assert manifest["commit_count"] == 0
        assert manifest["object_count"] == 0
        assert manifest["content_root"] == sha(b"")
        assert manifest["batches"] == []
        assert (out / "checksum-report.tsv").read_text() == "batch_id\tlogical_key\trelative_path\tsize\tsha256\tsidecar_sha256\n"
        assert_provenance(out, manifest, [])

    def test_committed_receipt_with_path_escape_is_rejected(self, tmp_path):
        """Committed object paths must stay under objects/<batch_id>/ and an invalid receipt must not update outputs."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        out.mkdir()
        for name in ["manifest.json", "checksum-report.tsv", "provenance.json"]:
            (out / name).write_text("previous\n")
        payload = b"outside\n"
        digest = sha(payload)
        batch_id = "escape-" + f"{1:03d}"
        manual = {
            "schema_version": 1,
            "batch_id": batch_id,
            "phase": "committed",
            "epoch": 9,
            "objects": [
                {
                    "logical_key": "escape",
                    "relative_path": f"objects/{batch_id}/../escape.dat",
                    "size": len(payload),
                    "sha256": digest,
                }
            ],
        }
        write_manual_receipt(store, batch_id, manual)
        result = run_cmd([str(BIN), "rebuild", "--store", str(store), "--out", str(out)], check=False)
        assert result.returncode != 0
        for name in ["manifest.json", "checksum-report.tsv", "provenance.json"]:
            assert (out / name).read_text() == "previous\n"

    def test_unlisted_payloads_inside_committed_batch_are_ignored(self, tmp_path):
        """A committed receipt's objects array is the publishable object list; extra files are not output rows."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        batch_id = "listed-a"
        write_batch(store, batch_id, "committed", 31, {"alpha": b"listed payload\n"})
        object_spec(store, batch_id, "extra", b"unlisted payload\n")

        run_cmd([str(BIN), "rebuild", "--store", str(store), "--out", str(out)])

        assert_bundle_matches_store(store, out)
        assert "extra" not in json.dumps(read_json(out / "manifest.json"))
        assert "unlisted payload" not in (out / "checksum-report.tsv").read_text()

    def test_payloads_without_receipts_do_not_create_batches(self, tmp_path):
        """Payloads and sidecars on disk are insufficient without a receipt."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        orphan_id = "orphan-a"
        write_batch(store, "visible-a", "committed", 41, {"alpha": b"visible\n"})
        object_spec(store, orphan_id, "loose", b"orphan payload\n")

        run_cmd([str(BIN), "rebuild", "--store", str(store), "--out", str(out)])

        assert_bundle_matches_store(store, out)
        manifest_text = json.dumps(read_json(out / "manifest.json"))
        report_text = (out / "checksum-report.tsv").read_text()
        assert orphan_id not in manifest_text
        assert "loose" not in report_text

    def test_duplicate_logical_keys_across_committed_batches_are_preserved(self, tmp_path):
        """The same logical key in different committed batches represents two receipt entries, not one global duplicate."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        write_batch(store, "dupe-a", "committed", 51, {"shared/key": b"first\n"})
        write_batch(store, "dupe-b", "committed", 52, {"shared/key": b"second\n"})

        run_cmd([str(BIN), "rebuild", "--store", str(store), "--out", str(out)])

        manifest = read_json(out / "manifest.json")
        assert manifest["object_count"] == 2
        manifest_batch_ids = [batch["batch_id"] for batch in manifest["batches"]]
        assert len(manifest_batch_ids) == 2
        assert len(set(manifest_batch_ids)) == 2
        assert_bundle_matches_store(store, out)

    def test_unsorted_receipt_objects_are_sorted_in_outputs(self, tmp_path):
        """Receipt object order must not leak into the manifest or report ordering."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        batch_id = "sort-a"
        objects = [
            object_spec(store, batch_id, "gamma", b"g\n"),
            object_spec(store, batch_id, "alpha", b"a\n"),
            object_spec(store, batch_id, "beta", b"b\n"),
        ]
        write_manual_receipt(
            store,
            batch_id,
            {"schema_version": 1, "batch_id": batch_id, "phase": "committed", "epoch": 61, "objects": objects},
        )

        run_cmd([str(BIN), "rebuild", "--store", str(store), "--out", str(out)])

        manifest = read_json(out / "manifest.json")
        expected_order = sorted(obj["logical_key"] for obj in objects)
        assert [obj["logical_key"] for obj in manifest["batches"][0]["objects"]] == expected_order
        assert_bundle_matches_store(store, out)

    def test_zero_byte_payload_has_empty_digest_and_zero_size(self, tmp_path):
        """A zero-byte payload is a valid committed object with size 0 and the empty-byte SHA-256."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        write_batch(store, "empty-a", "committed", 71, {"blank": b""})

        run_cmd([str(BIN), "rebuild", "--store", str(store), "--out", str(out)])

        obj = read_json(out / "manifest.json")["batches"][0]["objects"][0]
        expected = committed_objects_from_receipts(store)[0]
        assert obj["logical_key"] == expected["logical_key"]
        assert obj["size"] == 0
        assert obj["sha256"] == sha(b"")
        assert_bundle_matches_store(store, out)

    def test_identical_store_contents_at_different_roots_produce_identical_outputs(self, tmp_path):
        """Output bytes must derive from store content, not from the store root path."""
        build_cli()
        store1 = tmp_path / "work" / "object-store"
        store2 = tmp_path / "app" / "object-store"
        out1 = tmp_path / "output"
        out2 = tmp_path / "app" / "output"
        write_batch(store1, "portable-a", "committed", 81, {"alpha": b"a\n"})
        write_batch(store1, "portable-b", "committed", 82, {"nested/beta": b"b\n"})
        shutil.copytree(store1, store2)

        run_cmd([str(BIN), "rebuild", "--store", str(store1), "--out", str(out1)])
        run_cmd([str(BIN), "rebuild", "--store", str(store2), "--out", str(out2)])

        for name in OUTPUT_NAMES:
            assert (out1 / name).read_bytes() == (out2 / name).read_bytes()

    def test_rebuild_creates_nested_missing_output_directory_with_full_bundle(self, tmp_path):
        """The product path creates a missing output directory and writes the complete user-visible bundle."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "app" / "work" / "output"
        write_batch(store, "nested-a", "committed", 91, {"alpha": b"alpha\n"})

        run_cmd([str(BIN), "rebuild", "--store", str(store), "--out", str(out)])

        assert sorted(path.name for path in out.iterdir()) == sorted(OUTPUT_NAMES)
        assert_bundle_matches_store(store, out)

    def test_invalid_object_metadata_in_non_committed_batch_is_ignored(self, tmp_path):
        """Object metadata in a non-committed receipt must not block valid committed batches."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        write_batch(store, "good-a", "committed", 101, {"alpha": b"good\n"})
        write_manual_receipt(
            store,
            "bad-prepared",
            {
                "schema_version": 1,
                "batch_id": "bad-prepared",
                "phase": "prepared",
                "epoch": 102,
                "objects": [
                    {
                        "logical_key": "bad",
                        "relative_path": f"objects/{'bad-prepared'}/../bad.dat",
                        "size": -1,
                        "sha256": "BAD",
                    }
                ],
            },
        )

        run_cmd([str(BIN), "rebuild", "--store", str(store), "--out", str(out)])

        assert_bundle_matches_store(store, out)
        assert "bad-prepared" not in json.dumps(read_json(out / "manifest.json"))

    def test_malformed_receipt_json_rejects_without_replacing_existing_outputs(self, tmp_path):
        """Malformed receipt JSON is a rebuild error and must not update existing output files."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        (store / "receipts").mkdir(parents=True)
        batch_id = "broken"
        (store / "receipts" / f"{batch_id}.receipt.json").write_text("{not json\n")

        assert_rebuild_fails_without_output_change(store, out)

    def test_unsupported_schema_version_rejects_without_replacing_existing_outputs(self, tmp_path):
        """Committed receipts must use schema_version 1."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        batch_id = "schema-a"
        spec = object_spec(store, batch_id, "alpha", b"alpha\n")
        write_manual_receipt(
            store,
            batch_id,
            {"schema_version": 2, "batch_id": batch_id, "phase": "committed", "epoch": 111, "objects": [spec]},
        )

        assert_rebuild_fails_without_output_change(store, out)

    def test_receipt_filename_batch_id_mismatch_rejects_without_replacing_existing_outputs(self, tmp_path):
        """A committed receipt's batch_id must match its receipt filename."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        body_id = "body-a"
        spec = object_spec(store, body_id, "alpha", b"alpha\n")
        write_manual_receipt(
            store,
            "file-a",
            {"schema_version": 1, "batch_id": body_id, "phase": "committed", "epoch": 121, "objects": [spec]},
        )

        assert_rebuild_fails_without_output_change(store, out)

    def test_non_integer_epoch_rejects_without_replacing_existing_outputs(self, tmp_path):
        """Committed receipt epochs must be integers."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        batch_id = "epoch-a"
        receipts = store / "receipts"
        receipts.mkdir(parents=True)
        (receipts / f"{batch_id}.receipt.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "batch_id": batch_id,
                    "phase": "committed",
                    "epoch": "121",
                    "objects": [],
                },
                indent=2,
            )
            + "\n"
        )

        assert_rebuild_fails_without_output_change(store, out)

    def test_missing_payload_rejects_without_replacing_existing_outputs(self, tmp_path):
        """Every object listed by a committed receipt must have a payload."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        batch_id = "miss-a"
        spec = object_spec(store, batch_id, "alpha", b"alpha\n", write_payload=False)
        write_manual_receipt(
            store,
            batch_id,
            {"schema_version": 1, "batch_id": batch_id, "phase": "committed", "epoch": 131, "objects": [spec]},
        )

        assert_rebuild_fails_without_output_change(store, out)

    def test_receipt_size_mismatch_rejects_without_replacing_existing_outputs(self, tmp_path):
        """Receipt size metadata must match the payload byte length."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        batch_id = "size-a"
        data = b"alpha\n"
        spec = object_spec(store, batch_id, "alpha", data, receipt_size=len(data) + 1)
        write_manual_receipt(
            store,
            batch_id,
            {"schema_version": 1, "batch_id": batch_id, "phase": "committed", "epoch": 141, "objects": [spec]},
        )

        assert_rebuild_fails_without_output_change(store, out)

    def test_receipt_sha_mismatch_rejects_without_replacing_existing_outputs(self, tmp_path):
        """Receipt sha256 metadata must match the payload digest."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        batch_id = "digest-a"
        spec = object_spec(store, batch_id, "alpha", b"alpha\n", receipt_sha="0" * 64)
        write_manual_receipt(
            store,
            batch_id,
            {"schema_version": 1, "batch_id": batch_id, "phase": "committed", "epoch": 151, "objects": [spec]},
        )

        assert_rebuild_fails_without_output_change(store, out)

    def test_uppercase_receipt_digest_rejects_without_replacing_existing_outputs(self, tmp_path):
        """Receipt sha256 values must be lowercase hex digests."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        batch_id = "uppercase-a"
        data = b"alpha\n"
        upper = sha(data).upper()
        spec = object_spec(store, batch_id, "alpha", data, receipt_sha=upper, sidecar_digest=upper)
        write_manual_receipt(
            store,
            batch_id,
            {"schema_version": 1, "batch_id": batch_id, "phase": "committed", "epoch": 161, "objects": [spec]},
        )

        assert_rebuild_fails_without_output_change(store, out)

    def test_missing_checksum_sidecar_rejects_without_replacing_existing_outputs(self, tmp_path):
        """Every committed payload must have a checksum sidecar."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        batch_id = "sidecar-a"
        spec = object_spec(store, batch_id, "alpha", b"alpha\n", write_sidecar=False)
        write_manual_receipt(
            store,
            batch_id,
            {"schema_version": 1, "batch_id": batch_id, "phase": "committed", "epoch": 171, "objects": [spec]},
        )

        assert_rebuild_fails_without_output_change(store, out)

    def test_relative_path_under_wrong_batch_prefix_rejects_without_replacing_existing_outputs(self, tmp_path):
        """A committed object relative_path must stay under objects/<batch_id>/."""
        build_cli()
        store = tmp_path / "store"
        out = tmp_path / "out"
        batch_id = "prefix-a"
        spec = object_spec(
            store,
            batch_id,
            "alpha",
            b"alpha\n",
            relative_path=f"objects/{'other-batch'}/alpha.dat",
        )
        write_manual_receipt(
            store,
            batch_id,
            {"schema_version": 1, "batch_id": batch_id, "phase": "committed", "epoch": 181, "objects": [spec]},
        )

        assert_rebuild_fails_without_output_change(store, out)
