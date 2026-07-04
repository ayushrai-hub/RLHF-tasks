#!/usr/bin/env python3
"""Independent reference for the exhibit signing audit.

Recomputes the reconciled catalog, signature evidence, and remediation report from
the local database, the live Trust Registry, and the media/signature fixtures. It is
written independently of the AWK library and is used both to cross-check the oracle
during generation and to grade agent output at verify time (no answer key is shipped
for the live scenario). Config is read from the audit contract.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import sqlite3
import subprocess
import tempfile
import tomllib
import urllib.request
from pathlib import Path


def load_config(app: Path) -> dict:
    contract = tomllib.loads((app / "config" / "audit_contract.toml").read_text(encoding="utf-8"))
    return {
        "audit_time": contract["time"]["audit_time"],
        "manifest_version": contract["manifest"]["version"],
        "retroactive_reasons": set(contract["revocation"]["retroactive_reasons"]),
        "rawin": set(contract["keys"]["rawin_algorithms"]),
        "registry_base": contract["registry"]["base_url"],
        "start_cursor": contract["registry"]["start_cursor"],
    }


def to_utc(ts: str | None) -> str | None:
    if ts is None or ts == "":
        return None
    moment = dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_registry(base: str, start_cursor: str) -> tuple[dict, dict]:
    records: dict[str, list] = {}
    cursor = start_cursor
    while cursor:
        page = _get(f"{base}/v1/keystates?cursor={cursor}")
        for rec in page["records"]:
            records.setdefault(rec["key_id"], []).append(rec)
        cursor = page.get("next_cursor")
    voids = {v["key_id"]: v for v in _get(f"{base}/v1/voids")["expunged"]}
    return records, voids


def reconcile(db_row: dict, recs: list, void: dict | None, audit_time: str) -> dict:
    effective = sorted(
        (r for r in recs if to_utc(r["as_of"]) <= audit_time), key=lambda r: r["revision"]
    )
    if effective:
        current = effective[-1]
        trusted = bool(current["trusted"])
        if void is not None:
            status, reason, revoked_at = "revoked", "key_expunged", void["expunged_at"]
        else:
            status = current["status"]
            reason = current["revocation_reason"]
            revoked_at = current["revoked_at"]
    elif void is not None:
        status, reason, revoked_at = "revoked", "key_expunged", void["expunged_at"]
        trusted = bool(db_row["trusted"])
    else:
        status = db_row["status"]
        trusted = bool(db_row["trusted"])
        reason = db_row["revocation_reason"]
        revoked_at = db_row["revoked_at"]
    return {
        "key_status": status,
        "key_trusted": trusted,
        "revocation_reason": reason,
        "revoked_at": to_utc(revoked_at),
    }


def _db(app: Path):
    con = sqlite3.connect(app / "data" / "exhibit_signing.db")
    con.row_factory = sqlite3.Row
    return con


def build_catalog(app: Path, cfg: dict | None = None) -> dict:
    cfg = cfg or load_config(app)
    con = _db(app)
    keys = {r["key_id"]: dict(r) for r in con.execute("SELECT * FROM keys")}
    images = [dict(r) for r in con.execute("SELECT * FROM images ORDER BY image_id")]
    exc = {r["image_id"]: dict(r) for r in con.execute("SELECT * FROM policy_exceptions")}
    con.close()
    records, voids = fetch_registry(cfg["registry_base"], cfg["start_cursor"])
    out = []
    for im in images:
        k = keys[im["key_id"]]
        rec = reconcile(k, records.get(k["key_id"], []), voids.get(k["key_id"]), cfg["audit_time"])
        e = exc.get(im["image_id"])
        out.append(
            {
                "image_id": im["image_id"],
                "media_path": im["media_path"],
                "signature_path": im["signature_path"],
                "key_id": k["key_id"],
                "algorithm": k["algorithm"],
                "digest_algorithm": k["digest_algorithm"],
                "key_fingerprint": k["fingerprint"],
                "public_key_path": k["public_key_path"],
                "key_status": rec["key_status"],
                "key_trusted": rec["key_trusted"],
                "key_not_before": to_utc(k["not_before"]),
                "key_not_after": to_utc(k["not_after"]),
                "revocation_reason": rec["revocation_reason"],
                "revoked_at": rec["revoked_at"],
                "signed_at": to_utc(im["signed_at"]),
                "exception_id": e["exception_id"] if e else None,
                "exception_expires_at": to_utc(e["expires_at"]) if e else None,
            }
        )
    out.sort(key=lambda c: c["image_id"])
    return {"suite": "exhibit-signing-audit", "revision": "2026-Q2", "audit_time": cfg["audit_time"], "row_count": len(out), "images": out}


def spki_fingerprint(pub: Path) -> str:
    der = subprocess.run(["openssl", "pkey", "-pubin", "-in", str(pub), "-outform", "DER"], capture_output=True, check=True).stdout
    return subprocess.run(["openssl", "dgst", "-sha256"], input=der, capture_output=True, check=True).stdout.decode().split()[-1]


def manifest_bytes(version: str, image_id: str, content_hex: str, signed_at_utc: str) -> bytes:
    return f"{version}\n{image_id}\nsha256={content_hex}\n{signed_at_utc}\n".encode("utf-8")


def verify_manifest(app: Path, entry: dict, cfg: dict, content_hex: str) -> bool:
    pub = app / entry["public_key_path"]
    sig = app / entry["signature_path"]
    with tempfile.TemporaryDirectory() as td:
        sigbin = Path(td) / "s.bin"
        man = Path(td) / "m"
        man.write_bytes(manifest_bytes(cfg["manifest_version"], entry["image_id"], content_hex, entry["signed_at"]))
        if subprocess.run(["openssl", "base64", "-d", "-in", str(sig), "-out", str(sigbin)], capture_output=True).returncode != 0:
            return False
        if entry["algorithm"] in cfg["rawin"]:
            cmd = ["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(pub), "-rawin", "-in", str(man), "-sigfile", str(sigbin)]
        else:
            cmd = ["openssl", "dgst", "-" + entry["digest_algorithm"], "-verify", str(pub), "-signature", str(sigbin), str(man)]
        return subprocess.run(cmd, capture_output=True).returncode == 0


def build_evidence(app: Path, catalog: dict, cfg: dict | None = None) -> dict:
    cfg = cfg or load_config(app)
    ev = []
    for entry in catalog["images"]:
        method = "pkeyutl" if entry["algorithm"] in cfg["rawin"] else "dgst"
        computed = spki_fingerprint(app / entry["public_key_path"])
        content = hashlib.sha256((app / entry["media_path"]).read_bytes()).hexdigest()
        match = computed == entry["key_fingerprint"]
        row = {
            "image_id": entry["image_id"],
            "key_id": entry["key_id"],
            "algorithm": entry["algorithm"],
            "verify_method": method,
            "computed_fingerprint": computed,
            "fingerprint_match": match,
            "content_sha256": content,
        }
        if not match:
            row.update(signature_valid=False, failure_reason="fingerprint_mismatch")
        else:
            valid = verify_manifest(app, entry, cfg, content)
            row.update(signature_valid=valid, failure_reason=None if valid else "signature_verification_failed")
        ev.append(row)
    return {"audit_time": cfg["audit_time"], "row_count": len(ev), "evidence": ev}


def classify(c: dict, e: dict, cfg: dict) -> tuple[str, str | None]:
    if not e["signature_valid"]:
        return "quarantine", e["failure_reason"]
    reason = c["revocation_reason"]
    if reason is not None:
        if reason in cfg["retroactive_reasons"]:
            return "quarantine", reason
        if c["signed_at"] >= c["revoked_at"]:
            return "quarantine", "signed_after_revocation"
    if not (c["key_not_before"] <= c["signed_at"] <= c["key_not_after"]):
        if c["exception_id"] and c["exception_expires_at"] >= cfg["audit_time"]:
            return "honor_exception", None
        return "quarantine", "signed_outside_validity"
    return ("accept", None) if c["key_status"] == "active" else ("reinstate", None)


def build_report(catalog: dict, evidence: dict, cfg: dict) -> dict:
    cat = {c["image_id"]: c for c in catalog["images"]}
    ev = {e["image_id"]: e for e in evidence["evidence"]}
    actions = []
    summary = {"accept": 0, "reinstate": 0, "honor_exception": 0, "quarantine": 0, "revoke_trust": 0}
    for iid in sorted(cat):
        act, reason = classify(cat[iid], ev[iid], cfg)
        actions.append({"image_id": iid, "key_id": cat[iid]["key_id"], "action": act, "reason": reason})
        summary[act] += 1
    key_actions, seen = [], set()
    for iid in sorted(cat):
        c = cat[iid]
        if c["key_id"] in seen:
            continue
        seen.add(c["key_id"])
        if c["key_status"] in ("retired", "revoked") and c["key_trusted"]:
            key_actions.append({"key_id": c["key_id"], "action": "revoke_trust", "status": c["key_status"]})
    key_actions.sort(key=lambda k: k["key_id"])
    summary["revoke_trust"] = len(key_actions)
    return {"audit_time": cfg["audit_time"], "image_actions": actions, "key_actions": key_actions, "summary": summary}


def compute_all(app: Path) -> dict:
    cfg = load_config(app)
    catalog = build_catalog(app, cfg)
    evidence = build_evidence(app, catalog, cfg)
    report = build_report(catalog, evidence, cfg)
    return {"catalog": catalog, "evidence": evidence, "report": report}


if __name__ == "__main__":
    import sys

    print(json.dumps(compute_all(Path(sys.argv[1])), indent=2))
