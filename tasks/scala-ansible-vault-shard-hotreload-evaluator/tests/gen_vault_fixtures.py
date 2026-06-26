"""Build `.vshard` bundles and row specs for vault shard hot-reload tests."""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

TENANT_ALPHA = "TENANT-ALPHA"
TENANT_BETA = "TENANT-BETA"
EPOCH_BASE = 1_700_000_000

SOURCE_BYTE = {"sidecar_mount": 0, "vault_file": 1, "env": 2}


def crc16_ccitt_false(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc & 0xFFFF


def _str_field(value: str) -> bytes:
    raw = value.encode("utf-8")
    return struct.pack(">H", len(raw)) + raw


def build_frame(
    *,
    shard_seq: int,
    tenant_id: str,
    shard_id: str,
    workload_id: str,
    material_source: str,
    reload_applied: bool,
    log_redacted: bool,
    secret_version: str,
    preview: str = "",
    bad_crc: bool = False,
    crc_includes_magic: bool = False,
) -> bytes:
    body = bytes([1, 0])
    body += struct.pack(">I", shard_seq)
    body += _str_field(tenant_id)
    body += _str_field(shard_id)
    body += _str_field(workload_id)
    body += bytes(
        [
            SOURCE_BYTE[material_source],
            1 if reload_applied else 0,
            1 if log_redacted else 0,
        ]
    )
    body += _str_field(secret_version)
    body += _str_field(preview)

    crc_input = (b"VS" + body) if crc_includes_magic else body
    crc = crc16_ccitt_false(crc_input)
    if bad_crc:
        crc = (crc + 1) & 0xFFFF
    return b"VS" + body + struct.pack(">H", crc)


def write_bundle(path: Path, frames: list[bytes], *, noise: bytes = b"") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(noise + b"".join(frames))


def _row(
    shard_id: str,
    tenant_id: str,
    shard_seq: int,
    workload_id: str,
    material_source: str,
    reload_applied: bool,
    log_redacted: bool,
    secret_version: str,
    preview: str | None = None,
) -> dict[str, Any]:
    return {
        "shard_id": shard_id,
        "tenant_id": tenant_id,
        "shard_seq": shard_seq,
        "workload_id": workload_id,
        "material_source": material_source,
        "reload_applied": reload_applied,
        "log_redacted": log_redacted,
        "secret_version": secret_version,
        "preview": preview,
    }


def ten_alpha_public_shards() -> list[dict[str, Any]]:
    """Rows stored after fixed ingest of the public bundle (3 frames)."""
    return [
        _row("sh-a1-env", TENANT_ALPHA, 1, "api", "env", True, True, "v1-env"),
        _row("sh-a2-env", TENANT_ALPHA, 2, "api", "env", True, True, "v2-env"),
        _row(
            "sh-w3-side",
            TENANT_ALPHA,
            3,
            "worker",
            "sidecar_mount",
            False,
            False,
            "w1",
            preview="sekret",
        ),
    ]


def public_bundle_frames() -> list[bytes]:
    """Physical order is not ascending shard_seq (ingest must sort)."""
    return [
        build_frame(
            shard_seq=3,
            tenant_id=TENANT_ALPHA,
            shard_id="sh-w3-side",
            workload_id="worker",
            material_source="sidecar_mount",
            reload_applied=False,
            log_redacted=False,
            secret_version="w1",
            preview="sekret",
        ),
        build_frame(
            shard_seq=1,
            tenant_id=TENANT_ALPHA,
            shard_id="sh-a1-env",
            workload_id="api",
            material_source="env",
            reload_applied=True,
            log_redacted=True,
            secret_version="v1-env",
        ),
        build_frame(
            shard_seq=2,
            tenant_id=TENANT_ALPHA,
            shard_id="sh-a2-env",
            workload_id="api",
            material_source="env",
            reload_applied=True,
            log_redacted=True,
            secret_version="v2-env",
        ),
    ]


def noise_resync_frames() -> list[bytes]:
    return public_bundle_frames()


def bad_crc_frames() -> list[bytes]:
    frames = public_bundle_frames()
    return [frames[0], build_frame(
        shard_seq=9,
        tenant_id=TENANT_ALPHA,
        shard_id="sh-bad",
        workload_id="bad",
        material_source="env",
        reload_applied=True,
        log_redacted=True,
        secret_version="x",
        bad_crc=True,
    )]


def mixed_tenant_frames() -> list[bytes]:
    return [
        build_frame(
            shard_seq=1,
            tenant_id=TENANT_ALPHA,
            shard_id="sh-mix-a",
            workload_id="api",
            material_source="env",
            reload_applied=True,
            log_redacted=True,
            secret_version="a",
        ),
        build_frame(
            shard_seq=2,
            tenant_id=TENANT_BETA,
            shard_id="sh-mix-b",
            workload_id="api",
            material_source="env",
            reload_applied=True,
            log_redacted=True,
            secret_version="b",
        ),
    ]


def precedence_trap_frames() -> list[bytes]:
    """Same shard_seq+workload; env must win after collapse."""
    return [
        build_frame(
            shard_seq=10,
            tenant_id=TENANT_ALPHA,
            shard_id="sh-v10",
            workload_id="pay",
            material_source="vault_file",
            reload_applied=True,
            log_redacted=True,
            secret_version="vault-only",
        ),
        build_frame(
            shard_seq=10,
            tenant_id=TENANT_ALPHA,
            shard_id="sh-e10",
            workload_id="pay",
            material_source="env",
            reload_applied=True,
            log_redacted=True,
            secret_version="env-wins",
        ),
    ]


def precedence_trap_shards() -> list[dict[str, Any]]:
    return [_row("sh-e10", TENANT_ALPHA, 10, "pay", "env", True, True, "env-wins")]


def reload_gate_frames() -> list[bytes]:
    return [
        build_frame(
            shard_seq=20,
            tenant_id=TENANT_ALPHA,
            shard_id="sh-gate",
            workload_id="gate",
            material_source="env",
            reload_applied=False,
            log_redacted=True,
            secret_version="pending-v",
        )
    ]


def reload_gate_shards() -> list[dict[str, Any]]:
    return [_row("sh-gate", TENANT_ALPHA, 20, "gate", "env", False, True, "pending-v")]


def duplicate_shard_frames() -> list[bytes]:
    """Two copies of an existing public shard_id (re-ingest skips both)."""
    frame = build_frame(
        shard_seq=1,
        tenant_id=TENANT_ALPHA,
        shard_id="sh-a1-env",
        workload_id="api",
        material_source="env",
        reload_applied=True,
        log_redacted=True,
        secret_version="v1-env",
    )
    return [frame, frame]


def conflict_cross_bundle_frames() -> list[bytes]:
    return [
        build_frame(
            shard_seq=7,
            tenant_id=TENANT_ALPHA,
            shard_id="sh-c7a",
            workload_id="conf",
            material_source="env",
            reload_applied=True,
            log_redacted=True,
            secret_version="first",
        )
    ]


def conflict_second_frames() -> list[bytes]:
    return [
        build_frame(
            shard_seq=7,
            tenant_id=TENANT_ALPHA,
            shard_id="sh-c7b",
            workload_id="conf",
            material_source="vault_file",
            reload_applied=True,
            log_redacted=True,
            secret_version="second",
        )
    ]


def tenant_beta_frames() -> list[bytes]:
    return [
        build_frame(
            shard_seq=1,
            tenant_id=TENANT_BETA,
            shard_id="sh-b1",
            workload_id="beta",
            material_source="vault_file",
            reload_applied=True,
            log_redacted=True,
            secret_version="b1",
        )
    ]


def tenant_beta_shards() -> list[dict[str, Any]]:
    return [_row("sh-b1", TENANT_BETA, 1, "beta", "vault_file", True, True, "b1")]


def beta_duplicate_frames() -> list[bytes]:
    frame = tenant_beta_frames()[0]
    return [frame, frame]


def hidden_ooo_frames() -> list[bytes]:
    """Physical file order 30, 10, 20 — ingest must sort by shard_seq before store."""
    return [
        build_frame(
            shard_seq=30,
            tenant_id=TENANT_ALPHA,
            shard_id="sh-h30",
            workload_id="hidden",
            material_source="env",
            reload_applied=True,
            log_redacted=True,
            secret_version="h30",
        ),
        build_frame(
            shard_seq=10,
            tenant_id=TENANT_ALPHA,
            shard_id="sh-h10",
            workload_id="hidden",
            material_source="env",
            reload_applied=True,
            log_redacted=True,
            secret_version="h10",
        ),
        build_frame(
            shard_seq=20,
            tenant_id=TENANT_ALPHA,
            shard_id="sh-h20",
            workload_id="hidden",
            material_source="env",
            reload_applied=True,
            log_redacted=True,
            secret_version="h20",
        ),
    ]


def hidden_precedence_shadow_frames() -> list[bytes]:
    """vault_file frame before env at same shard_seq — env must win after collapse."""
    return [
        build_frame(
            shard_seq=40,
            tenant_id=TENANT_ALPHA,
            shard_id="sh-hv40",
            workload_id="shadow",
            material_source="vault_file",
            reload_applied=True,
            log_redacted=True,
            secret_version="vault-shadow",
        ),
        build_frame(
            shard_seq=40,
            tenant_id=TENANT_ALPHA,
            shard_id="sh-he40",
            workload_id="shadow",
            material_source="env",
            reload_applied=True,
            log_redacted=True,
            secret_version="env-shadow",
        ),
    ]


def write_public_fixture(target: Path | None = None) -> Path:
    path = target or Path(__file__).resolve().parents[1] / "environment/app/fixtures/public/sample_bundle.vshard"
    write_bundle(path, public_bundle_frames())
    return path


def write_hidden_fixtures(fixtures_dir: Path | None = None) -> None:
    root = fixtures_dir or Path(__file__).resolve().parent / "fixtures"
    root.mkdir(parents=True, exist_ok=True)
    write_bundle(root / "hidden_ooo.vshard", hidden_ooo_frames())
    write_bundle(root / "hidden_precedence.vshard", hidden_precedence_shadow_frames())


if __name__ == "__main__":
    out = write_public_fixture()
    write_hidden_fixtures()
    print(f"wrote {out} ({out.stat().st_size} bytes)")
