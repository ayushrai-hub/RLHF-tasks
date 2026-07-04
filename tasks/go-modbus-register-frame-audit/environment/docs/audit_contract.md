# Audit contract

Report JSON is a flat object (no wrapper envelopes). Keys:

- `api_version` (int, always 1)
- `segment` (int, requested bus segment filter)
- `mreg_files` (JSON array of `.mreg` basenames in scan order; `[]` when the directory has none, never `null`)
- `frame_count` (int, frames after duplicate-seq collapse in the segment)
- `register_read_count` (int, sum of `count` on successful `0x03` read frames)
- `crc_failure_count` (int, frames rejected by Modbus CRC16)
- `exception_count` (int, frames with function code >= `0x80`)
- `chain_root_hex` (64-char hex rolling digest over collapsed read payloads)
- `duplicate_seq_drops` (int, frames dropped while collapsing duplicate sequence ids)
- `slave_reject_count` (int, segment frames rejected by the allow-list)
- `checkpoint_skip_count` (int, `0x00` checkpoint markers removed before collapse)
- `min_reg` / `max_reg` (int, address span over collapsed segment reads)
- `active_slave_count` (int, distinct slaves with successful reads after collapse)

Scan order honors `.mregorder` sidecars when present. Continuation scans with `.mreg_continue` seed the rolling digest from `/app/out/.mregtip` when that file exists beside the report output directory.

Successful audits persist `/app/out/.mregtip` with the computed `chain_root_hex`.

## Processing pipeline

Frames from all `.mreg` capture files (in scan order) pass through these stages:

1. **CRC validation** — frames failing Modbus CRC16 increment `crc_failure_count` and are omitted.
2. **Checkpoint removal** — function code `0x00` markers increment `checkpoint_skip_count` and are omitted from later stages.
3. **Segment filter and allow-list reject** — keep only frames on the requested segment. Frames whose slave id is not listed in `/app/environment/data/slave_allowlist.txt` increment `slave_reject_count` and are omitted. Allow-list rejection runs on the segment stream **before** duplicate-sequence collapse; rejected rows never participate in deduplication or chain walks.
4. **Duplicate-sequence collapse** — within the post-reject segment stream, frames sharing a sequence id collapse to the last row; dropped rows increment `duplicate_seq_drops`.
5. **Chain and summary** — `chain_root_hex`, register totals, exception counts, and `min_reg` / `max_reg` are computed on the collapsed segment stream.

### Rolling digest (`chain_root_hex`)

64-character lowercase hex string. Start from 64 zero digits, or from the trimmed contents of `/app/out/.mregtip` when a continuation scan seeds from durable output. Walk the collapsed segment stream in order; omit checkpoint (`0x00`) and exception (`≥0x80`) rows. For each remaining frame, replace the digest with the SHA-256 hex digest (`sha256` of `prior_digest + ":" + payload_bytes`), where `payload_bytes` is the raw on-wire payload field from the frame header.
