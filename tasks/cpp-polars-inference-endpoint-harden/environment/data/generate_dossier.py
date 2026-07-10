"""Build the inference operations dossier at image build time (>= 60k tokens)."""
from __future__ import annotations

import hashlib
import os
import textwrap

OUT = "/app/docs/inference-operations-dossier.md"

OPERATIVE = """# Inference Operations Dossier — Ridge Batch Scoring Fleet

**Document ID:** ML-INF-RIDGE-2026-v3.2  
**Custodian:** Platform ML Serving — Batch Control Board (BCB)

Practitioners must read this dossier in full. Section 12 (Amendment Register) supersedes earlier preprocessing defaults in Sections 4–5.

---

## Section 1 — Fleet scope

The ridge batch scorer serves tabular scoring requests on port 19091. A C++ `score-server` validates each batch, probes the Polars sidecar lockfile at `/app/environment/sidecar/poetry.lock`, invokes `/app/environment/sidecar/feature_pipe/preprocess.py` for feature generation, and emits deterministic weighted scores from `/app/environment/config/model_weights.json`.

---

## Section 2 — Model card archive (reference)

Model cards are informational. Scoring uses the bundled ridge weights file.

| Card ID | Family | Notes |
|---------|--------|-------|
| ridge-v3 | tabular | default production weights |

---

## Section 3 — Incident thread digest (historical)

Threads BCB-201 through BCB-288 document null-fill drift, lockfile bypass attempts, and oversize batch incidents. None of those threads change the ratified policy; see Section 12.

---

## Section 4 — Preprocessing defaults (initial ratification)

Initial values below were superseded by Amendment P-2026-03 in Section 12.

| Field | Initial value |
|-------|----------------|
| max_batch_rows | 128 |
| null_fill | zero |
| unknown_category | bucket |
| polars_pin | 0.20.31 |
| score_precision | 4 |

---

## Section 5 — Sidecar invocation (initial)

Initial ratification allowed `FEATURE_NULL_MODE=zero` and skipped lock probing when the sidecar wheel was present on disk.

---

## Section 6 — HTTP surface

`POST /v1/batch-score` accepts JSON with keys `batch_id` (string) and `rows` (array). Each row object requires `row_id`, `age` (number or null), `tenure_months` (number or null), `region` (string), and `channel` (string). Approved regions: `west`, `east`, `north`, `south`. Approved channels: `web`, `phone`, `retail`.

---

## Section 7 — Feature generation

The Polars sidecar emits per-row feature maps with keys `age_ff`, `tenure_ff`, exactly one hot `region_*` key set to `1.0`, and exactly one hot `channel_*` key set to `1.0`. Numeric nulls in `age` and `tenure_months` are forward-filled down the batch row order before normalization. Normalization divides `age` by `100.0` and `tenure_months` by `60.0`.

`feature_digest` is the first 16 lowercase hex characters of SHA-256 over UTF-8 bytes of canonical feature JSON with sorted keys for that row.

---

## Section 8 — Scoring rule

Each score is the dot product of the feature map with ridge weights plus `bias`, then rounded to `score_precision` decimal places using standard round-half-away-from-zero (`std::round` semantics on the scaled value).

---

## Section 9 — Rejection semantics

Oversize batches, rows with missing required keys, and rows with unknown `region` or `channel` values must be rejected without invoking the sidecar. Rejected rows appear in the response `scores` array with `status` `rejected` and HTTP-level batch handling still returns 200 with tallies. When the lock probe fails, the entire batch fails closed with `rejected` equal to row count and no `ok` rows.

---

## Section 10 — Audit report schema

`/app/output/batch_audit.json` root keys: `api_version` (`"1"`), `policy_seq`, `lock_digest`, `accepted` (integer), `rejected` (integer), `scores` (array sorted ascending by `row_id`).

Each score object keys: `row_id`, `score` (number when `status` is `ok`, else null), `feature_digest` (string when `ok`, else null), `status` (`ok` or `rejected`).

`policy_seq` is the first 16 lowercase hex characters of SHA-256 over UTF-8 bytes of canonical policy JSON with sorted keys: `max_batch_rows`, `null_fill`, `unknown_category`, `polars_pin`, `score_precision`. Derive it from the extracted policy object, not a static table.

`lock_digest` is the first 16 lowercase hex characters of SHA-256 over UTF-8 bytes of the string `polars==<polars_pin>` where `<polars_pin>` is the ratified pin from Section 12.

---

## Section 11 — Lockfile gate

Before launching the sidecar, read `/app/environment/sidecar/poetry.lock` and verify the `polars` package entry matches the ratified `polars_pin`. Any mismatch must fail closed for the batch.

---

## Section 12 — Amendment Register

| Amendment | Date | Supersedes | Operative values |
|-----------|------|------------|------------------|
| P-2026-03 | 2026-03-18 | Sections 4–5 | max_batch_rows **32**; null_fill **forward**; unknown_category **reject**; polars_pin **1.12.0**; score_precision **6** |

The sidecar must receive `FEATURE_NULL_MODE=forward` matching the ratified `null_fill` value.

---

"""

FILLER = """
## Appendix {idx} — Deployment chatter {idx}

{text}

"""


def main() -> None:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    parts = [OPERATIVE]
    paragraph = (
        "On-call noted batch depth, reran score diff, and attached feature-card PDFs. "
        "No policy change implied."
    )
    idx = 1
    while sum(len(p) for p in parts) < 250_000:
        block = textwrap.fill(paragraph * 4, width=100)
        parts.append(FILLER.format(idx=idx, text=block))
        idx += 1
    body = "\n".join(parts)
    doc_digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(body)
        fh.write(f"\n<!-- dossier_digest={doc_digest} -->\n")
    print(f"wrote {OUT} chars={len(body)}")


if __name__ == "__main__":
    main()
