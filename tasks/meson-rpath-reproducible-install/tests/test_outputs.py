import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path("/app/environment")
WORK = Path("/app/work/capsule")
PREFIX = WORK / "install"
OUT = Path("/app/output")
MANIFEST = OUT / "install_manifest.json"
LEDGER = WORK / "install_ledger.json"
EXPECTED_PACKAGE = "capsule-meson-rpath-2.7.4"
EXPECTED_VERSION = "2.7.4"
EXPECTED_SCHEMA = "capsule-install-manifest-v1"
EXPECTED_LEDGER_SCHEMA = "capsule-install-ledger-v1"
EXPECTED_HEADER = "include/capsule_config.h"
EXPECTED_PROFILE = "release"


def expected_rpath():
    notes = (ROOT / "docs/packaging_notes.md").read_text()
    for token in ("$ORIGIN/../lib",):
        if token in notes:
            return token
    raise AssertionError("packaging notes must document the libexec-relative loader token")

_INSTALL_CACHE = {"installed": False, "manifest": None, "ledger": None}


def run_cmd(command, *, cwd=ROOT, env=None, expect=0):
    merged = os.environ.copy()
    if env:
        merged.update(env)
    result = subprocess.run(
        command,
        cwd=cwd,
        env=merged,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == expect, (
        f"command {command} returned {result.returncode}, expected {expect}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result


def reset_all():
    shutil.rmtree(WORK, ignore_errors=True)
    shutil.rmtree(OUT, ignore_errors=True)
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)


def invalidate_install_cache():
    _INSTALL_CACHE["installed"] = False
    _INSTALL_CACHE["manifest"] = None
    _INSTALL_CACHE["ledger"] = None


def package_once():
    reset_all()
    run_cmd(["make", "smoke"])
    run_cmd(["make", "package"])
    assert MANIFEST.exists(), "package pipeline did not write the install manifest"
    assert LEDGER.exists(), "package pipeline did not write the install ledger"
    manifest = json.loads(MANIFEST.read_text())
    ledger = json.loads(LEDGER.read_text())
    _INSTALL_CACHE["installed"] = True
    _INSTALL_CACHE["manifest"] = manifest
    _INSTALL_CACHE["ledger"] = ledger
    return manifest, ledger


def package_fresh_again():
    run_cmd(["make", "package"])
    assert MANIFEST.exists(), "package pipeline did not write the install manifest"
    assert LEDGER.exists(), "package pipeline did not write the install ledger"
    manifest = json.loads(MANIFEST.read_text())
    ledger = json.loads(LEDGER.read_text())
    _INSTALL_CACHE["installed"] = True
    _INSTALL_CACHE["manifest"] = manifest
    _INSTALL_CACHE["ledger"] = ledger
    return manifest, ledger


def ensure_installed():
    if not _INSTALL_CACHE["installed"]:
        return package_once()
    return _INSTALL_CACHE["manifest"], _INSTALL_CACHE["ledger"]


def replay_once():
    run_cmd(["make", "replay"])
    assert MANIFEST.exists(), "replay did not rewrite the install manifest"
    manifest = json.loads(MANIFEST.read_text())
    ledger = json.loads(LEDGER.read_text())
    _INSTALL_CACHE["manifest"] = manifest
    _INSTALL_CACHE["ledger"] = ledger
    return manifest, ledger


def reconcile_once(*, expect=0):
    run_cmd(["bash", "scripts/pipeline.sh", "reconcile"], expect=expect)


def sha256_file(path):
    result = run_cmd(["sha256sum", str(path)], cwd=Path("/app"))
    return result.stdout.split()[0]


def parse_pairs(text):
    result = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def read_dynamic_path(binary):
    result = run_cmd(["readelf", "-d", str(binary)])
    for line in result.stdout.splitlines():
        if "RUNPATH" in line or "RPATH" in line:
            return line.split("[", 1)[1].split("]", 1)[0]
    return ""


def tree_by_path(manifest):
    return {entry["path"]: entry for entry in manifest["tree"]}


def installed_paths_non_dir():
    return sorted(
        str(path.relative_to(PREFIX))
        for path in PREFIX.rglob("*")
        if not path.is_dir()
    )


def read_header_define(name):
    text = (PREFIX / EXPECTED_HEADER).read_text()
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "#define" and parts[1] == name:
            return parts[2].strip('"')
    raise AssertionError(f"missing define {name} in installed header")


def run_installed_binary(name, *, cwd=Path("/tmp")):
    env = os.environ.copy()
    env.pop("LD_LIBRARY_PATH", None)
    return run_cmd([str(PREFIX / "bin" / name)], cwd=cwd, env=env)


def compute_tree_root(manifest):
    lines = sorted(f"{entry['path']}:{entry['sha256']}" for entry in manifest["tree"])
    payload = "\n".join(lines).encode("utf-8")
    result = subprocess.run(
        ["sha256sum"],
        input=payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return result.stdout.decode().split()[0]


def assert_manifest_shape(manifest):
    assert manifest["schema"] == EXPECTED_SCHEMA
    assert manifest["prefix"] == str(PREFIX)
    assert manifest["build_system"] == "meson"
    assert set(manifest) == {
        "schema",
        "prefix",
        "build_system",
        "ledger",
        "runtime",
        "config",
        "tree",
    }
    assert set(manifest["ledger"]) == {"generation", "catalog_epoch", "tree_root_sha256"}
    assert isinstance(manifest["tree"], list) and len(manifest["tree"]) >= 7


def assert_release_values(manifest):
    runtime = manifest["runtime"]
    config = manifest["config"]
    ledger = manifest["ledger"]
    assert runtime["binary"] == "bin/capsule-info"
    assert runtime["ld_library_path"] == ""
    assert runtime["rpath"] == expected_rpath()
    assert runtime["compiled"] == {
        "package_id": EXPECTED_PACKAGE,
        "version": EXPECTED_VERSION,
        "source": "generated",
        "provenance": "meson-configured",
        "profile": EXPECTED_PROFILE,
    }
    assert runtime["linked"] == {
        "package_id": EXPECTED_PACKAGE,
        "version": EXPECTED_VERSION,
        "source": "generated",
        "provenance": "meson-configured",
        "origin": "installed",
        "profile": EXPECTED_PROFILE,
    }
    assert config["header"] == EXPECTED_HEADER
    assert config["version"] == EXPECTED_VERSION
    assert config["package_id"] == EXPECTED_PACKAGE
    assert config["source"] == "generated"
    assert config["provenance"] == "meson-configured"
    assert config["profile"] == EXPECTED_PROFILE
    assert ledger["catalog_epoch"] == EXPECTED_PROFILE
    assert ledger["tree_root_sha256"] == compute_tree_root(manifest)


def assert_ledger_shape(ledger, manifest):
    assert ledger["schema"] == EXPECTED_LEDGER_SCHEMA
    assert ledger["generation"] == manifest["ledger"]["generation"]
    assert ledger["catalog_epoch"] == manifest["ledger"]["catalog_epoch"]
    assert ledger["last_manifest_sha256"] == sha256_file(MANIFEST)


def test_fresh_package_establishes_consistent_ledger():
    """A fresh package run writes aligned manifest and sidecar ledger records."""
    manifest, ledger = package_once()
    assert_manifest_shape(manifest)
    assert_release_values(manifest)
    assert isinstance(manifest["ledger"]["generation"], int)
    assert manifest["ledger"]["generation"] >= 1
    assert_ledger_shape(ledger, manifest)
    reconcile_once()


def test_installed_binaries_carry_relative_loader_paths():
    """Installed executables embed the prefix-independent loader path."""
    manifest, _ledger = ensure_installed()
    for name in ("capsule-info", "capsule-consumer"):
        binary = PREFIX / "bin" / name
        assert binary.exists(), f"missing installed binary {binary}"
        path_note = read_dynamic_path(binary)
        assert path_note == expected_rpath()
        assert str(PREFIX) not in path_note
    assert manifest["runtime"]["rpath"] == expected_rpath()


def test_installed_commands_run_without_loader_environment():
    """Installed diagnostic and consumer commands run with no loader search path."""
    ensure_installed()
    info = parse_pairs(run_installed_binary("capsule-info").stdout)
    consumer = parse_pairs(run_installed_binary("capsule-consumer").stdout)
    assert info["linked_origin"] == "installed"
    assert info["compiled_profile"] == EXPECTED_PROFILE
    assert info["linked_profile"] == EXPECTED_PROFILE
    assert consumer["consumer_origin"] == "installed"
    assert consumer["consumer_profile"] == EXPECTED_PROFILE
    assert consumer["consumer_package_id"] == EXPECTED_PACKAGE


def test_config_header_is_generated_and_matches_manifest():
    """The shipped header is configured output rather than the source-tree fallback."""
    manifest, _ledger = ensure_installed()
    header = PREFIX / EXPECTED_HEADER
    text = header.read_text()
    assert "@CAPSULE_" not in text
    assert "source-fallback" not in text
    assert "checked-in" not in text
    assert manifest["config"]["sha256"] == sha256_file(header)
    assert manifest["config"]["package_id"] == read_header_define("CAPSULE_PACKAGE_ID")


def test_manifest_tree_rows_match_installed_files():
    """Tree rows describe every installed file with live digests and modes."""
    manifest, _ledger = ensure_installed()
    seen = tree_by_path(manifest)
    required = {
        "bin/capsule-info",
        "bin/capsule-consumer",
        "include/capsule.h",
        EXPECTED_HEADER,
        "lib/pkgconfig/capsule.pc",
    }
    assert required.issubset(seen)
    assert sorted(seen) == installed_paths_non_dir()
    for rel, entry in seen.items():
        path = PREFIX / rel
        assert entry["sha256"] == sha256_file(path)
        assert entry["mode"] == format(path.stat().st_mode & 0o777, "o")


def test_soname_symlink_rows_use_resolved_target_metadata():
    """Soname links record target content digests and permission modes."""
    manifest, _ledger = ensure_installed()
    seen = tree_by_path(manifest)
    assert "lib/libcapsule.so.2" in seen
    assert "lib/libcapsule.so" in seen
    for rel, entry in seen.items():
        path = PREFIX / rel
        if not path.is_symlink():
            continue
        target = path.resolve()
        assert target.is_file(), f"soname link {rel} must resolve to a regular file"
        assert entry["sha256"] == sha256_file(target)
        assert entry["mode"] == format(path.stat().st_mode & 0o777, "o")


def test_tree_root_digest_is_derived_from_manifest_tree_rows():
    """The ledger tree root matches a recomputation from manifest tree rows."""
    manifest, _ledger = ensure_installed()
    assert manifest["ledger"]["tree_root_sha256"] == compute_tree_root(manifest)


def test_replay_preserves_ledger_generation():
    """Resumed installs keep the ledger generation stable across replay."""
    manifest, ledger = package_once()
    generation = manifest["ledger"]["generation"]
    replay_manifest, replay_ledger = replay_once()
    assert replay_manifest["ledger"]["generation"] == generation
    assert replay_ledger["generation"] == generation


def test_replay_regenerates_identical_manifest_bytes():
    """Replay rewrites a byte-for-byte equivalent manifest."""
    first, _ledger = package_once()
    first_text = json.dumps(first, sort_keys=True, separators=(",", ":"))
    second, _ledger2 = replay_once()
    second_text = json.dumps(second, sort_keys=True, separators=(",", ":"))
    assert second_text == first_text


def test_replay_chain_and_reconcile_stay_aligned():
    """Repeated replay runs keep manifest, ledger, and reconcile in agreement."""
    package_once()
    for _ in range(2):
        replay_once()
        reconcile_once()


def test_fresh_package_after_replay_resets_generation():
    """A later fresh package run resets generation instead of continuing a stale counter."""
    manifest, _ledger = package_once()
    initial_generation = manifest["ledger"]["generation"]
    replay_once()
    manifest, ledger = package_fresh_again()
    assert manifest["ledger"]["generation"] == initial_generation
    assert ledger["generation"] == initial_generation


def test_reconcile_rejects_stale_sidecar_generation():
    """Reconcile fails when the sidecar ledger generation drifts from the manifest."""
    ensure_installed()
    ledger = json.loads(LEDGER.read_text())
    ledger["generation"] = ledger["generation"] + 5
    LEDGER.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
    reconcile_once(expect=4)


def test_reconcile_rejects_corrupted_tree_root():
    """Reconcile fails when the recorded tree root no longer matches the tree section."""
    manifest, _ledger = package_once()
    manifest["ledger"]["tree_root_sha256"] = "0" * 64
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    reconcile_once(expect=5)


def test_release_audit_does_not_record_loader_shortcuts():
    """Release manifest runtime metadata must not claim loader search path help."""
    manifest, _ledger = ensure_installed()
    assert manifest["runtime"]["ld_library_path"] == ""
    assert manifest["runtime"]["linked"]["origin"] == "installed"


def test_runtime_metadata_matches_diagnostic_and_consumer_output():
    """Manifest runtime metadata stays aligned with installed command output."""
    manifest, _ledger = ensure_installed()
    info = parse_pairs(run_installed_binary("capsule-info").stdout)
    consumer = parse_pairs(run_installed_binary("capsule-consumer").stdout)
    linked = manifest["runtime"]["linked"]
    assert linked["package_id"] == info["linked_package_id"]
    assert linked["origin"] == info["linked_origin"]
    assert linked["profile"] == info["linked_profile"]
    assert consumer == {
        "consumer_package_id": EXPECTED_PACKAGE,
        "consumer_provenance": "meson-configured",
        "consumer_origin": "installed",
        "consumer_profile": EXPECTED_PROFILE,
    }


def test_tampered_manifest_is_replaced_by_package_pipeline():
    """Hand-edited manifest output is discarded when packaging runs again."""
    package_once()
    MANIFEST.write_text('{"schema":"tampered"}')
    invalidate_install_cache()
    run_cmd(["make", "package"])
    manifest = json.loads(MANIFEST.read_text())
    assert_manifest_shape(manifest)
    assert_release_values(manifest)


def test_deleted_install_prefix_is_rebuilt_by_replay():
    """Removing installed artifacts and replaying restores a consistent release tree."""
    package_once()
    shutil.rmtree(PREFIX)
    invalidate_install_cache()
    manifest, ledger = replay_once()
    assert (PREFIX / "bin" / "capsule-info").exists()
    assert_manifest_shape(manifest)
    assert_ledger_shape(ledger, manifest)
    reconcile_once()


def test_smoke_build_does_not_emit_install_manifest():
    """Smoke validates the build tree without writing release manifest output."""
    reset_all()
    invalidate_install_cache()
    run_cmd(["make", "smoke"])
    assert not MANIFEST.exists()
    assert not LEDGER.exists()


def test_binaries_run_from_unrelated_working_directory():
    """Installed commands stay runnable from outside the install prefix."""
    ensure_installed()
    info = parse_pairs(run_installed_binary("capsule-info", cwd=Path("/tmp")).stdout)
    consumer = parse_pairs(run_installed_binary("capsule-consumer", cwd=Path("/tmp")).stdout)
    assert info["linked_origin"] == "installed"
    assert consumer["consumer_origin"] == "installed"
