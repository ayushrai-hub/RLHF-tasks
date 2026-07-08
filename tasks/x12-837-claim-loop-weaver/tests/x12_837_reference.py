"""
Independent X12 837 claim loop weaver per /app/docs/837-weave.md.
"""

from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


def _errors_digest(errors: list[str]) -> str:
    lines = sorted(errors)
    payload = "\n".join(lines)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _format_money(value: str) -> str:
    dec = Decimal(value)
    return str(dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _read_isa_delimiters(isa_body: str) -> tuple[str, str]:
    if len(isa_body) < 105:
        return "*", ":"
    return isa_body[3], isa_body[104]


def _split_segments(raw: str) -> list[str]:
    parts = re.split(r"~|\r?\n", raw)
    return [part for part in parts if part.strip()]


def _parse_segment(raw: str, elem_sep: str) -> tuple[str, list[str]]:
    fields = raw.split(elem_sep)
    seg_id = fields[0] if fields else ""
    return seg_id, fields


def _normalize_patient_name(last: str) -> str:
    return last.replace("\u00a0", " ").strip(" ")


def _parse_hi_codes(hi_fields: list[str], comp_sep: str) -> list[str]:
    codes: list[str] = []
    for element in hi_fields[1:]:
        if not element:
            continue
        parts = element.split(comp_sep)
        if len(parts) >= 2 and parts[1]:
            codes.append(parts[1])
        elif parts[0]:
            codes.append(parts[0])
    return codes


def _pointer_list_from_sv1(sv1_fields: list[str], comp_sep: str) -> list[str]:
    if len(sv1_fields) <= 7 or not sv1_fields[7]:
        return []
    return [part for part in sv1_fields[7].split(comp_sep) if part]


def _parse_frequency(clm_fields: list[str], comp_sep: str) -> str:
    if len(clm_fields) <= 5 or not clm_fields[5]:
        return "1"
    parts = clm_fields[5].split(comp_sep)
    if len(parts) >= 3 and parts[2]:
        return parts[2]
    return "1"


def _parse_procedure(sv1_fields: list[str], comp_sep: str) -> str:
    if len(sv1_fields) <= 1 or not sv1_fields[1]:
        return ""
    parts = sv1_fields[1].split(comp_sep)
    if len(parts) >= 2 and parts[1]:
        return parts[1]
    if parts[0]:
        return parts[0]
    return ""


def weave_shards(
    shards_dir: Path,
    manifest_path: Path,
) -> tuple[dict, dict, list[str], int]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    shard_files = sorted(shards_dir.glob("*.edi"))

    errors: list[str] = []
    skipped = 0

    claims: dict[str, dict] = {}

    for shard_path in shard_files:
        priority = int(manifest.get(shard_path.name, 0))
        raw_text = shard_path.read_text(encoding="utf-8")
        segments_raw = _split_segments(raw_text)
        if not segments_raw:
            continue

        elem_sep, comp_sep = _read_isa_delimiters(segments_raw[0])

        current_claim: str | None = None
        current_lx: int | None = None
        inherited_pointers: list[str] = []

        for seg_raw in segments_raw:
            seg_id, fields = _parse_segment(seg_raw, elem_sep)

            if seg_id == "ISA":
                elem_sep, comp_sep = _read_isa_delimiters(seg_raw)
                continue

            if seg_id == "CLM":
                if len(fields) < 2 or not fields[1]:
                    errors.append(f"{shard_path.name}: {seg_raw}")
                    skipped += 1
                    continue
                control = fields[1]
                current_claim = control
                current_lx = None
                inherited_pointers = []
                claim = claims.setdefault(
                    control,
                    {
                        "control_number": control,
                        "priority": priority,
                        "clm_fields": fields,
                        "patient_name": "",
                        "subscriber_id": "",
                        "ref_f8": "",
                        "comp_sep": comp_sep,
                        "lines": {},
                    },
                )
                if priority >= claim["priority"]:
                    claim["priority"] = priority
                    claim["clm_fields"] = fields
                    claim["comp_sep"] = comp_sep
                continue

            if seg_id == "NM1":
                if len(fields) < 4:
                    errors.append(f"{shard_path.name}: {seg_raw}")
                    skipped += 1
                    continue
                qualifier = fields[1]
                if qualifier not in {"QC", "IL", "82", "85"}:
                    errors.append(f"{shard_path.name}: {seg_raw}")
                    skipped += 1
                    continue
                if current_claim is None:
                    continue
                claim = claims[current_claim]
                if priority < claim["priority"]:
                    continue
                if qualifier == "QC":
                    last = _normalize_patient_name(fields[3])
                    first = fields[4] if len(fields) > 4 else ""
                    claim["patient_name"] = f"{last} {first}".strip()
                elif qualifier == "IL" and len(fields) > 9:
                    claim["subscriber_id"] = fields[9]
                continue

            if seg_id == "REF":
                if current_claim is None:
                    continue
                claim = claims[current_claim]
                if priority < claim["priority"]:
                    continue
                if len(fields) > 2 and fields[1] == "F8":
                    claim["ref_f8"] = fields[2]
                continue

            if seg_id == "LX":
                if len(fields) < 2 or not fields[1].isdigit() or int(fields[1]) < 1:
                    errors.append(f"{shard_path.name}: {seg_raw}")
                    skipped += 1
                    continue
                if current_claim is None:
                    errors.append(f"{shard_path.name}: {seg_raw}")
                    skipped += 1
                    continue
                current_lx = int(fields[1])
                claim = claims[current_claim]
                line = claim["lines"].setdefault(
                    current_lx,
                    {
                        "lx_sequence": current_lx,
                        "priority": priority,
                        "sv1_fields": None,
                        "hi_codes": None,
                        "inherited_pointers": list(inherited_pointers),
                    },
                )
                if priority >= line["priority"]:
                    line["priority"] = priority
                    line["inherited_pointers"] = list(inherited_pointers)
                continue

            if seg_id == "SV1":
                if len(fields) < 2 or not _parse_procedure(fields, comp_sep):
                    errors.append(f"{shard_path.name}: {seg_raw}")
                    skipped += 1
                    continue
                if current_claim is None or current_lx is None:
                    errors.append(f"{shard_path.name}: {seg_raw}")
                    skipped += 1
                    continue
                claim = claims[current_claim]
                line = claim["lines"].setdefault(
                    current_lx,
                    {
                        "lx_sequence": current_lx,
                        "priority": priority,
                        "sv1_fields": None,
                        "hi_codes": None,
                        "inherited_pointers": list(inherited_pointers),
                    },
                )
                if priority >= line["priority"]:
                    line["priority"] = priority
                    line["sv1_fields"] = fields
                continue

            if seg_id == "HI":
                if current_claim is None or current_lx is None:
                    continue
                claim = claims[current_claim]
                line = claim["lines"].setdefault(
                    current_lx,
                    {
                        "lx_sequence": current_lx,
                        "priority": priority,
                        "sv1_fields": None,
                        "hi_codes": None,
                        "inherited_pointers": list(inherited_pointers),
                    },
                )
                if priority >= line["priority"]:
                    line["priority"] = priority
                    line["hi_codes"] = _parse_hi_codes(fields, comp_sep)
                    inherited_pointers = [
                        str(idx) for idx in range(1, len(line["hi_codes"]) + 1)
                    ]
                continue

    output_claims: list[dict] = []
    for control in sorted(claims):
        claim = claims[control]
        clm_fields = claim["clm_fields"]
        comp_sep = claim.get("comp_sep", ":")
        freq = _parse_frequency(clm_fields, comp_sep)
        service_lines: list[dict] = []
        inherited: list[str] = []
        for lx_seq in sorted(claim["lines"]):
            line = claim["lines"][lx_seq]
            sv1 = line["sv1_fields"]
            if sv1 is None:
                continue
            if line["hi_codes"] is not None:
                inherited = [str(i) for i in range(1, len(line["hi_codes"]) + 1)]
                pointers = _pointer_list_from_sv1(sv1, comp_sep)
                if not pointers:
                    pointers = list(inherited)
            else:
                pointers = _pointer_list_from_sv1(sv1, comp_sep)
                if not pointers:
                    pointers = list(inherited)
            service_lines.append(
                {
                    "lx_sequence": lx_seq,
                    "procedure": _parse_procedure(sv1, comp_sep),
                    "charge": _format_money(sv1[2] if len(sv1) > 2 else "0"),
                    "diagnosis_pointers": pointers,
                }
            )
            if line["hi_codes"] is not None:
                inherited = [str(i) for i in range(1, len(line["hi_codes"]) + 1)]

        output_claims.append(
            {
                "control_number": control,
                "patient_name": claim["patient_name"],
                "subscriber_id": claim["subscriber_id"],
                "total_charge": _format_money(clm_fields[2] if len(clm_fields) > 2 else "0"),
                "frequency_code": freq,
                "service_lines": service_lines,
                "_ref_f8": claim["ref_f8"],
            }
        )

    remove: set[str] = set()
    for claim in output_claims:
        if claim["frequency_code"] == "7" and claim["_ref_f8"]:
            remove.add(claim["_ref_f8"])

    final_claims = []
    for claim in output_claims:
        if claim["control_number"] in remove:
            continue
        claim.pop("_ref_f8", None)
        final_claims.append(claim)

    summary = {
        "claim_count": len(final_claims),
        "service_line_count": sum(len(c["service_lines"]) for c in final_claims),
        "skipped_segments": skipped,
        "manifest_fingerprint": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "errors_digest": _errors_digest(errors),
        "export_epoch": 1,
    }
    errors.sort()
    return {"claims": final_claims}, summary, errors, skipped


def build_outputs(
    shards_dir: Path | None = None,
    manifest_path: Path | None = None,
) -> tuple[dict, dict, list[str], int]:
    shards_dir = shards_dir or Path("/app/data/shards")
    manifest_path = manifest_path or Path("/app/data/shard-manifest.json")
    return weave_shards(shards_dir, manifest_path)
