# The Warmline Descriptor Format: A Migration Chronicle

Internal engineering record for the edge-CDN warm-cache planner. This document is the
ONLY surviving specification of the warm-cache descriptor file (`warmcache.dat`). It was
assembled by merging five revisions of design notes, incident write-ups, and review
threads, so it carries a great deal of history that no longer applies. Read it as a
chronicle: each revision superseded the previous one, and ONLY the latest revision
('descriptor revision 5', abbreviated R5) describes the file you must parse today.
Wherever an example, table, or rule is tagged with an older revision (R1..R4) it is kept
for historical accountability and MUST NOT be used to decode current descriptor files.

## 0. How to read this chronicle

The planner has kept the same broad shape since the beginning: the descriptor file is a
list of frames; each frame carries one record; records describe cache objects and their
hit weights and are reconciled into a warm-up order; the order is folded into a plan
digest. What changed across revisions was the frame envelope, the payload encoding, the
integrity check, the record grammar, the reconciliation rule, the ordering tie-break, and
the digest accumulator. Because each of those seven concerns changed at least once, a
reader who lifts a rule from the wrong chapter produces a plausible but wrong planner. The
safe approach: first establish which revision is current (Chapter 1), then collect that
revision's rule from each of the seven concern-chapters, ignoring every paragraph or
example marked with a superseded tag.

## 1. Revision timeline (which format is current)

The descriptor file is versioned by an integer 'descriptor revision' number. The timeline
below is authoritative for deciding which revision is live. There is deliberately NO
version marker inside `warmcache.dat` itself; the live revision is whichever one this
chronicle declares current.

- **R1** (decommissioned). The original pipe-delimited prototype. Frames were `seq|payload|sum` with a naive additive checksum, and payloads were raw ASCII. Abandoned after the delimiter-collision incident when object keys began to contain punctuation.
- **R2** (decommissioned). Introduced base32 payloads and a tab-delimited envelope, but kept the additive checksum. Withdrawn when the tab envelope broke the spreadsheet importers and base32 padding confused the length accounting.
- **R3** (decommissioned). Switched payload transport to lowercase hex and payload integrity to an MD5 prefix. Rolled back: MD5 was overkill and the hex transport doubled the file size on a hot path.
- **R4** (decommissioned). Adopted a CRC, specifically the POSIX `cksum` CRC, but computed over the BASE64 TEXT of the payload and stored together with the payload byte count, mimicking `cksum`'s two-number output. This 'checksum the transport, not the content' choice caused the silent-corruption class of tickets.
- **R5** (CURRENT). The revision in production today. CANONICAL base64 payloads, POSIX `cksum` CRC computed over the DECODED bytes (CRC value only, no byte count), a two-record grammar (OBJ/HIT) reconciled by an inner join on the key, C-locale (bytewise) ordering, and a djb2 plan accumulator. Everything you implement must target R5.

Takeaway: **R5 is current.** Every other revision is decommissioned. The remaining
chapters each open with historical context (which you may skim) and close with a clearly
marked 'R5 rule' (which you must follow).

## 2. The frame envelope

Historically the envelope has been the most-churned part of the format. R1 (decommissioned) used a pipe as the field separator: a frame looked like `41|<payload>|<sum>`, and because payloads could contain pipes it needed escaping and ultimately failed. R2 (decommissioned) moved to a TAB separator; several appendix examples still show tab-separated fields and will mis-split under R5.

R3 and R4 (both decommissioned) experimented with a trailing length field and an inline revision marker respectively; neither survived. The R4 marker in particular is a trap for readers of this chronicle: R4 frames carried a literal `r4` token, so some R4 examples below look like they have four fields. Current frames have exactly three.

A frame is one physical line. Blank lines (empty or whitespace-only) are not frames and are skipped without error, although the R2 importer treated them as fatal; that strictness was dropped.

### R5 rule (current)

- A frame is one line with EXACTLY three fields separated by a single ASCII space: `SEQ PAYLOAD CRC`.
- `SEQ` is a positive decimal integer with no leading zeros (the frame sequence number; sequence numbers need not be contiguous or sorted in the file).
- `PAYLOAD` is the encoded record (Chapter 3).
- `CRC` is the decimal integrity value (Chapter 4).
- A line that does not split into exactly three space-separated fields is invalid with code `BAD_FRAME`; if a sequence number can still be read from its first field (a positive integer with no leading zeros) report that number, otherwise report -1.
- The separator is a single space, never a tab or a pipe; those were R2 and R1.

### Worked examples

> [R1] `41|T09J...|317` is a pipe-delimited R1 frame; the pipe separator is gone.
> [R4] `88 T0JKIFFRIC0= 12345 r4` shows the R4 four-field frame with its trailing `r4` marker; current frames have three fields and no marker.
> [R5] `14 SElUIFFRIDc= 773844878` is a valid current frame: sequence 14, a canonical base64 payload, and a decimal CRC.

## 3. Payload encoding

The payload encoding is the single most common source of decoder bugs, because four different encodings appear in this chronicle. R1 (decommissioned) carried raw ASCII payloads with escaping. R2 (decommissioned) used base32 (the RFC-4648 base32 alphabet, `A-Z2-7`); many longer appendix examples are STILL base32 and will decode to garbage if you base64-decode them. R3 (decommissioned) used lowercase hex.

R5 uses CANONICAL RFC-4648 base64 (the standard alphabet `A-Za-z0-9+/` with `=` padding). Canonical means the payload must be exactly what a conformant base64 encoder would emit: length a multiple of four, correct `=` padding, and NO non-canonical trailing bits. In particular base64url (which uses `-` and `_` instead of `+` and `/`) is NOT accepted, and an unpadded string is NOT accepted. Decoding a canonical base64 payload yields the record bytes, which are ASCII text (Chapter 5).

### R5 rule (current)

- `PAYLOAD` is CANONICAL RFC-4648 base64 over the standard alphabet `A-Za-z0-9+/` with `=` padding; its length is a positive multiple of four.
- Decoding must round-trip: re-encoding the decoded bytes must reproduce the payload exactly (this rejects non-canonical padding/trailing bits).
- A payload that is empty, not a multiple of four in length, contains a character outside the standard base64 alphabet (for example the base64url `-`/`_`), is mis-padded, or does not round-trip, is invalid with code `BAD_B64`.
- The decoded bytes must be printable/ASCII (bytes 0x00..0x7f); a payload that decodes to a non-ASCII byte is a well-formed base64 but an invalid record, code `BAD_REC` (Chapter 5).
- Do NOT base32-decode (that was R2), do NOT hex-decode (that was R3), and do NOT accept base64url.

### Worked examples

> [R2] `J5BEUICRKEQC2===` is an R2 base32 payload; under R5 it is not valid base64 and is `BAD_B64`.
> [R3] `4849542051512033` is an R3 hex payload; under R5 hex text is (usually) not canonical base64 and must not be hex-decoded.
> [R5] `T0JKIFFRIC0=` is a canonical base64 payload decoding to the ASCII record `OBJ QQ -`.

## 4. Integrity checksum

This chapter is the heart of the silent-corruption story and the rule most often copied from the wrong revision. R1/R2 (decommissioned) used a trivial additive checksum (sum of payload bytes modulo 2^16); do not use it. R3 (decommissioned) used an MD5 prefix; do not use it.

R4 (decommissioned) is the dangerous one, because it used the RIGHT algorithm on the WRONG input. R4 computed the POSIX `cksum` CRC, but over the BASE64 TEXT of the payload (the transport), and it stored the value together with the payload byte count, mimicking `cksum`'s two-number output. Reusing the R4 rule on R5 frames passes the casual eye and fails on the wire, because R5 checks the CONTENT, not the transport, and stores only the CRC.

The 'POSIX cksum CRC' means precisely the algorithm `/usr/bin/cksum` uses: a CRC-32 with polynomial 0x04C11DB7, no input or output reflection, the message LENGTH appended to the stream (least-significant byte first) before the final complement with 0xFFFFFFFF. It is NOT the common zlib/Ethernet CRC-32. The number `cksum` prints in its FIRST column is exactly this value.

### R5 rule (current)

- `CRC` is the decimal POSIX `cksum` CRC of the DECODED payload BYTES (the record string, after base64-decoding), and ONLY that CRC value (no byte count).
- A frame whose `CRC` field is non-numeric, or is a valid non-negative integer but unequal to the cksum CRC of its decoded bytes, is invalid with code `BAD_CRC`.
- Checksum the CONTENT (decoded bytes), not the transport (base64 text): the R4 'checksum the base64' rule is decommissioned.
- The value `0` is a legal CRC field; only treat a CRC field as malformed when it is not a non-negative decimal integer (no leading zeros except the literal `0`).

### Worked examples

> [R4] An R4 frame stored `cksum(base64_text)` plus a byte count (two numbers); R5 stores one number, `cksum(decoded_bytes)`. For payload `T0JKIFFRIFJS` those two CRCs differ (1405427057 over the base64 text vs 2922817325 over the decoded bytes).
> [R5] For decoded bytes `OBJ QQ RR` the current CRC field is `cksum` of those exact bytes: `2922817325`.

## 5. Record grammar

The record carried by a frame has been a two-kind grammar since R3, but the kinds and field layout drifted. R3 (decommissioned) used `NODE`/`COST` as the two kinds and a colon separator. R5 uses `OBJ` and `HIT` and a single space separator, matching the envelope's separator.

Keys also changed shape: R2 keys were lowercase and unbounded; R5 keys are short uppercase tokens. Because the ordering tie-break (Chapter 7) is a bytewise C-locale comparison, the uppercase fixed-shape key matters: it makes the order a pure ASCII comparison.

An `OBJ` record names a cache object and its prerequisite objects (objects that must be warmed first); a `HIT` record names an object and its integer hit weight. The two are reconciled by key in Chapter 6.

### R5 rule (current)

- A decoded record is one of two kinds, split on single spaces into EXACTLY three tokens:
  - `OBJ <key> <prereqs>` where `<prereqs>` is either `-` (no prerequisites) or a comma-separated list of keys, split on commas exactly as `cut -d, -f-` would (no surrounding spaces, no empty fields).
  - `HIT <key> <w>` where `<w>` is a non-negative decimal integer of at most nine digits (no leading zeros except the literal `0`).
- A `<key>` matches `[A-Z][A-Z0-9]{1,5}`: an uppercase letter then one to five uppercase letters or digits, total length two to six.
- Codes for a well-formed frame whose RECORD is malformed: `BAD_REC` (not three space-separated tokens, or non-ASCII decoded bytes), `BAD_KIND` (first token not `OBJ`/`HIT`), `BAD_KEY` (the key token is not a key), `BAD_PRE` (a prerequisite token is not a key), `BAD_HITS` (the weight is not a valid non-negative integer).
- A second valid `OBJ` for a key already seen as an `OBJ`, or a second valid `HIT` for a key already seen as a `HIT`, is invalid with code `DUP`; the FIRST occurrence wins and later duplicates are recorded in the invalid list. An `OBJ` and a `HIT` for the same key are NOT duplicates (that is the normal join in Chapter 6).

### Worked examples

> [R3] `NODE:QQ:RR` is an R3 colon record; R5 uses spaces and `OBJ`/`HIT`.
> [R5] `OBJ QQ RR,SS` is an object QQ with prerequisites RR and SS; `HIT QQ 40` is its hit weight.

## 6. Reconciliation (the inner join)

Reconciliation has always been a join of the object records against the weight records, but the JOIN TYPE changed. R2 (decommissioned) used an OUTER join, inventing a zero weight for objects with no weight record; that produced phantom warm-ups and was withdrawn. R5 uses a strict INNER join: an object participates in the plan only if it has BOTH an OBJ record and a HIT record.

The join is on the key, over the DISTINCT valid records that survived Chapter 5 (first occurrence wins per Chapter 5's DUP rule). Think of it as `join` over two key-sorted streams, keeping only matched keys.

### R5 rule (current)

- The JOINED set is exactly the keys that have BOTH a valid OBJ record and a valid HIT record (an inner join on the key).
- Objects with an OBJ but no HIT, or a HIT but no OBJ, are NOT in the plan (no outer join, no invented weights).
- A prerequisite listed by a joined object that is not itself in the joined set is a DANGLING prerequisite: report it, but it does not add the missing key to the plan.
- The joined set is reported ascending by key (C-locale/bytewise).

### Worked examples

> [R2] R2 outer-joined and gave weightless objects weight 0; R5 drops them from the plan entirely.
> [R5] If OBJ exists for QQ, RR, SS but HIT exists only for QQ and RR, the joined set is `QQ, RR`; any prerequisite SS is dangling.

## 7. Ordering (warm-up order and tie-break)

The warm-up order is a topological sort: every prerequisite must be warmed before the object that needs it. What changed is the TIE-BREAK among objects that are simultaneously ready. R3 (decommissioned) broke ties by descending hit weight; R4 (decommissioned) broke ties by original frame sequence number. R5 breaks ties by the KEY in C-locale (bytewise ASCII) ascending order, which is why keys are uppercase fixed-shape tokens.

Concretely: maintain the set of objects whose (in-plan) prerequisites are all already placed; repeatedly emit the C-locale-smallest such key, then release its dependents. This is a Kahn-style topological sort with a bytewise-smallest-ready tie-break. If a cycle among joined objects prevents completion, the plan is not resolvable.

### R5 rule (current)

- Order the joined objects so that every in-plan prerequisite appears before the object that lists it (a topological order).
- Among objects that are ready simultaneously (all in-plan prerequisites already placed), always emit the one whose key is smallest in C-locale (bytewise ASCII) order. Do NOT tie-break by hit weight (R3) or by sequence number (R4).
- Dangling prerequisites (Chapter 6) impose no ordering constraint.
- If the joined objects contain a dependency cycle so that no full order exists, the plan is NOT resolvable; report resolvable=false and an empty order.

### Worked examples

> [R3] R3 emitted the heaviest ready object first; R5 emits the C-locale-smallest key first.
> [R5] If QQ (needs nothing) and RR (needs nothing) are both ready, QQ is emitted before RR because `QQ` < `RR` bytewise.

## 8. Plan digest (the accumulator)

The final stage folds the completed order into a compact digest for the deploy log. The accumulator changed across revisions: R2 (decommissioned) summed weights only; R4 (decommissioned) used an FNV-1a hash of the concatenated keys. R5 uses a djb2 rolling hash over the order's key bytes, alongside the total hit weight and a POSIX cksum of the newline-joined order.

The djb2 hash starts at 5381 and, for each byte b of each key taken in warm-up order, updates as `h = ((h * 33) XOR b) mod 2^32`. The keys are hashed with no separator between them, in warm-up order. Separately, the order is written one key per line (each key followed by a single newline) and the POSIX cksum CRC of that exact blob is the `order_crc`. The `hit_sum` is the plain integer sum of the joined objects' hit weights.

### R5 rule (current)

- If the plan is not resolvable, `plan_hash`, `hit_sum` and `order_crc` are all null.
- `plan_hash` is a djb2 hash over the warm-up order: start at 5381; for each byte b of each key, in order, with no separators, set `h = ((h * 33) XOR b) & 0xFFFFFFFF`.
- `hit_sum` is the integer sum of the hit weights of the joined objects.
- `order_crc` is the POSIX `cksum` CRC of the order written one key per line (each key followed by `\n`), i.e. `cksum` of `key1\nkey2\n...`.
- Do NOT use FNV-1a (R4) and do NOT sum weights alone (R2).

### Worked examples

> [R4] R4 hashed the order with FNV-1a; R5 uses djb2 seeded at 5381 with multiplier 33.
> [R5] For order `QQ, RR` the plan_hash folds the bytes of `QQRR`; the order_crc is `cksum` of `QQ\nRR\n`.

## 9. Appendix A: decommissioned worked examples (DO NOT IMPLEMENT)

The following worked examples are retained from the R1..R4 eras for historical
accountability. Each is tagged with its revision. They are deliberately voluminous and
deliberately WRONG for R5; they restate old inputs and their old-era interpretations. None
of them describes the file you must parse today. They are here so that a keyword search
for `OBJ`, `HIT`, `cksum`, or `base64` lands on far more superseded text than current text.

### R1 decommissioned examples

The following R1 frames use the pipe-delimited, raw ASCII payload, additive checksum envelope. Every one is superseded; they are shown so that the historical shape is on record and so that a reader who greps for record keywords sees the superseded era in bulk. Do not port any of these to R5.

> [R1] frame `100|OBJ HP1 -|529` carried the object record `OBJ HP1 -` under R1 framing (superseded).
> [R1] frame `101|HIT HP1 101|640` carried the weight record `HIT HP1 101` under R1 framing (superseded).
> [R1] Under R1, object `HP1` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `101|OBJ JW4 Z1B|701` carried the object record `OBJ JW4 Z1B` under R1 framing (superseded).
> [R1] frame `102|HIT JW4 138|662` carried the weight record `HIT JW4 138` under R1 framing (superseded).
> [R1] Under R1, object `JW4` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `102|OBJ K37 A8E|654` carried the object record `OBJ K37 A8E` under R1 framing (superseded).
> [R1] frame `103|HIT K37 175|631` carried the weight record `HIT K37 175` under R1 framing (superseded).
> [R1] Under R1, object `K37` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `103|OBJ LAA BFH,BFH|949` carried the object record `OBJ LAA BFH,BFH` under R1 framing (superseded).
> [R1] frame `104|HIT LAA 212|648` carried the weight record `HIT LAA 212` under R1 framing (superseded).
> [R1] Under R1, object `LAA` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `104|OBJ MHD -|545` carried the object record `OBJ MHD -` under R1 framing (superseded).
> [R1] frame `105|HIT MHD 249|669` carried the weight record `HIT MHD 249` under R1 framing (superseded).
> [R1] Under R1, object `MHD` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `105|OBJ NQG DVP|747` carried the object record `OBJ NQG DVP` under R1 framing (superseded).
> [R1] frame `106|HIT NQG 286|683` carried the weight record `HIT NQG 286` under R1 framing (superseded).
> [R1] Under R1, object `NQG` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `106|OBJ PXK E2S,E2S|974` carried the object record `OBJ PXK E2S,E2S` under R1 framing (superseded).
> [R1] frame `107|HIT PXK 323|688` carried the weight record `HIT PXK 323` under R1 framing (superseded).
> [R1] Under R1, object `PXK` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `107|OBJ Q4N F9V|707` carried the object record `OBJ Q4N F9V` under R1 framing (superseded).
> [R1] frame `108|HIT Q4N 360|657` carried the weight record `HIT Q4N 360` under R1 framing (superseded).
> [R1] Under R1, object `Q4N` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `108|OBJ RBR -|558` carried the object record `OBJ RBR -` under R1 framing (superseded).
> [R1] frame `109|HIT RBR 397|686` carried the weight record `HIT RBR 397` under R1 framing (superseded).
> [R1] Under R1, object `RBR` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `109|OBJ SJU HP1,HP1|971` carried the object record `OBJ SJU HP1,HP1` under R1 framing (superseded).
> [R1] frame `110|HIT SJU 434|690` carried the weight record `HIT SJU 434` under R1 framing (superseded).
> [R1] Under R1, object `SJU` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `110|OBJ TRX JW4|750` carried the object record `OBJ TRX JW4` under R1 framing (superseded).
> [R1] frame `111|HIT TRX 471|703` carried the weight record `HIT TRX 471` under R1 framing (superseded).
> [R1] Under R1, object `TRX` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `111|OBJ UY0 K37|686` carried the object record `OBJ UY0 K37` under R1 framing (superseded).
> [R1] frame `112|HIT UY0 508|672` carried the weight record `HIT UY0 508` under R1 framing (superseded).
> [R1] Under R1, object `UY0` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `112|OBJ V53 -|518` carried the object record `OBJ V53 -` under R1 framing (superseded).
> [R1] frame `113|HIT V53 545|641` carried the weight record `HIT V53 545` under R1 framing (superseded).
> [R1] Under R1, object `V53` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `113|OBJ WC6 MHD|708` carried the object record `OBJ WC6 MHD` under R1 framing (superseded).
> [R1] frame `114|HIT WC6 582|660` carried the weight record `HIT WC6 582` under R1 framing (superseded).
> [R1] Under R1, object `WC6` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `114|OBJ XK9 NQG|733` carried the object record `OBJ XK9 NQG` under R1 framing (superseded).
> [R1] frame `115|HIT XK9 619|673` carried the weight record `HIT XK9 619` under R1 framing (superseded).
> [R1] Under R1, object `XK9` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `115|OBJ YSC PXK,PXK|1052` carried the object record `OBJ YSC PXK,PXK` under R1 framing (superseded).
> [R1] frame `116|HIT YSC 656|693` carried the weight record `HIT YSC 656` under R1 framing (superseded).
> [R1] Under R1, object `YSC` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `116|OBJ ZZF -|578` carried the object record `OBJ ZZF -` under R1 framing (superseded).
> [R1] frame `117|HIT ZZF 693|705` carried the weight record `HIT ZZF 693` under R1 framing (superseded).
> [R1] Under R1, object `ZZF` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `117|OBJ A6J RBR|706` carried the object record `OBJ A6J RBR` under R1 framing (superseded).
> [R1] frame `118|HIT A6J 730|640` carried the weight record `HIT A6J 730` under R1 framing (superseded).
> [R1] Under R1, object `A6J` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `118|OBJ BDM SJU,SJU|1022` carried the object record `OBJ BDM SJU,SJU` under R1 framing (superseded).
> [R1] frame `119|HIT BDM 767|668` carried the weight record `HIT BDM 767` under R1 framing (superseded).
> [R1] Under R1, object `BDM` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `119|OBJ CLQ TRX|761` carried the object record `OBJ CLQ TRX` under R1 framing (superseded).
> [R1] frame `120|HIT CLQ 804|673` carried the weight record `HIT CLQ 804` under R1 framing (superseded).
> [R1] Under R1, object `CLQ` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `120|OBJ DTT -|564` carried the object record `OBJ DTT -` under R1 framing (superseded).
> [R1] frame `121|HIT DTT 841|686` carried the weight record `HIT DTT 841` under R1 framing (superseded).
> [R1] Under R1, object `DTT` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `121|OBJ E0W V53,V53|911` carried the object record `OBJ E0W V53,V53` under R1 framing (superseded).
> [R1] frame `122|HIT E0W 878|664` carried the weight record `HIT E0W 878` under R1 framing (superseded).
> [R1] Under R1, object `E0W` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `122|OBJ F7Z WC6|706` carried the object record `OBJ F7Z WC6` under R1 framing (superseded).
> [R1] frame `123|HIT F7Z 915|667` carried the weight record `HIT F7Z 915` under R1 framing (superseded).
> [R1] Under R1, object `F7Z` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `123|OBJ GE2 XK9|693` carried the object record `OBJ GE2 XK9` under R1 framing (superseded).
> [R1] frame `124|HIT GE2 952|643` carried the weight record `HIT GE2 952` under R1 framing (superseded).
> [R1] Under R1, object `GE2` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `124|OBJ HM5 -|530` carried the object record `OBJ HM5 -` under R1 framing (superseded).
> [R1] frame `125|HIT HM5 989|665` carried the weight record `HIT HM5 989` under R1 framing (superseded).
> [R1] Under R1, object `HM5` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `125|OBJ JU8 ZZF|748` carried the object record `OBJ JU8 ZZF` under R1 framing (superseded).
> [R1] frame `126|HIT JU8 1026|709` carried the weight record `HIT JU8 1026` under R1 framing (superseded).
> [R1] Under R1, object `JU8` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `126|OBJ K1B A6J|666` carried the object record `OBJ K1B A6J` under R1 framing (superseded).
> [R1] frame `127|HIT K1B 1063|685` carried the weight record `HIT K1B 1063` under R1 framing (superseded).
> [R1] Under R1, object `K1B` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `127|OBJ L8E BDM,BDM|950` carried the object record `OBJ L8E BDM,BDM` under R1 framing (superseded).
> [R1] frame `128|HIT L8E 1100|688` carried the weight record `HIT L8E 1100` under R1 framing (superseded).
> [R1] Under R1, object `L8E` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `128|OBJ MFH -|547` carried the object record `OBJ MFH -` under R1 framing (superseded).
> [R1] frame `129|HIT MFH 1137|716` carried the weight record `HIT MFH 1137` under R1 framing (superseded).
> [R1] Under R1, object `MFH` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `129|OBJ NNL DTT|751` carried the object record `OBJ NNL DTT` under R1 framing (superseded).
> [R1] frame `130|HIT NNL 1174|730` carried the weight record `HIT NNL 1174` under R1 framing (superseded).
> [R1] Under R1, object `NNL` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `130|OBJ PVP E0W,E0W|981` carried the object record `OBJ PVP E0W,E0W` under R1 framing (superseded).
> [R1] frame `131|HIT PVP 1211|736` carried the weight record `HIT PVP 1211` under R1 framing (superseded).
> [R1] Under R1, object `PVP` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `131|OBJ Q2S F7Z|712` carried the object record `OBJ Q2S F7Z` under R1 framing (superseded).
> [R1] frame `132|HIT Q2S 1248|714` carried the weight record `HIT Q2S 1248` under R1 framing (superseded).
> [R1] Under R1, object `Q2S` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `132|OBJ R9V -|553` carried the object record `OBJ R9V -` under R1 framing (superseded).
> [R1] frame `133|HIT R9V 1285|726` carried the weight record `HIT R9V 1285` under R1 framing (superseded).
> [R1] Under R1, object `R9V` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `133|OBJ SGY HM5,HM5|974` carried the object record `OBJ SGY HM5,HM5` under R1 framing (superseded).
> [R1] frame `134|HIT SGY 1322|736` carried the weight record `HIT SGY 1322` under R1 framing (superseded).
> [R1] Under R1, object `SGY` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `134|OBJ TP1 JU8|711` carried the object record `OBJ TP1 JU8` under R1 framing (superseded).
> [R1] frame `135|HIT TP1 1359|716` carried the weight record `HIT TP1 1359` under R1 framing (superseded).
> [R1] Under R1, object `TP1` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `135|OBJ UW4 K1B|697` carried the object record `OBJ UW4 K1B` under R1 framing (superseded).
> [R1] frame `136|HIT UW4 1396|728` carried the weight record `HIT UW4 1396` under R1 framing (superseded).
> [R1] Under R1, object `UW4` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `136|OBJ V37 -|520` carried the object record `OBJ V37 -` under R1 framing (superseded).
> [R1] frame `137|HIT V37 1433|688` carried the weight record `HIT V37 1433` under R1 framing (superseded).
> [R1] Under R1, object `V37` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `137|OBJ WAA MFH|719` carried the object record `OBJ WAA MFH` under R1 framing (superseded).
> [R1] frame `138|HIT WAA 1470|714` carried the weight record `HIT WAA 1470` under R1 framing (superseded).
> [R1] Under R1, object `WAA` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `138|OBJ XHD NNL|743` carried the object record `OBJ XHD NNL` under R1 framing (superseded).
> [R1] frame `139|HIT XHD 1507|726` carried the weight record `HIT XHD 1507` under R1 framing (superseded).
> [R1] Under R1, object `XHD` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `139|OBJ YQG PVP,PVP|1060` carried the object record `OBJ YQG PVP,PVP` under R1 framing (superseded).
> [R1] frame `140|HIT YQG 1544|740` carried the weight record `HIT YQG 1544` under R1 framing (superseded).
> [R1] Under R1, object `YQG` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `140|OBJ ZXK -|581` carried the object record `OBJ ZXK -` under R1 framing (superseded).
> [R1] frame `141|HIT ZXK 1581|753` carried the weight record `HIT ZXK 1581` under R1 framing (superseded).
> [R1] Under R1, object `ZXK` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `141|OBJ A4N R9V|703` carried the object record `OBJ A4N R9V` under R1 framing (superseded).
> [R1] frame `142|HIT A4N 1618|696` carried the weight record `HIT A4N 1618` under R1 framing (superseded).
> [R1] Under R1, object `A4N` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `142|OBJ BBR SGY,SGY|1027` carried the object record `OBJ BBR SGY,SGY` under R1 framing (superseded).
> [R1] frame `143|HIT BBR 1655|716` carried the weight record `HIT BBR 1655` under R1 framing (superseded).
> [R1] Under R1, object `BBR` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `143|OBJ CJU TP1|722` carried the object record `OBJ CJU TP1` under R1 framing (superseded).
> [R1] frame `144|HIT CJU 1692|729` carried the weight record `HIT CJU 1692` under R1 framing (superseded).
> [R1] Under R1, object `CJU` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `144|OBJ DRX -|566` carried the object record `OBJ DRX -` under R1 framing (superseded).
> [R1] frame `145|HIT DRX 1729|742` carried the weight record `HIT DRX 1729` under R1 framing (superseded).
> [R1] Under R1, object `DRX` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `145|OBJ EY0 V37,V37|917` carried the object record `OBJ EY0 V37,V37` under R1 framing (superseded).
> [R1] frame `146|HIT EY0 1766|711` carried the weight record `HIT EY0 1766` under R1 framing (superseded).
> [R1] Under R1, object `EY0` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `146|OBJ F53 WAA|674` carried the object record `OBJ F53 WAA` under R1 framing (superseded).
> [R1] frame `147|HIT F53 1803|671` carried the weight record `HIT F53 1803` under R1 framing (superseded).
> [R1] Under R1, object `F53` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `147|OBJ GC6 XHD|703` carried the object record `OBJ GC6 XHD` under R1 framing (superseded).
> [R1] frame `148|HIT GC6 1840|690` carried the weight record `HIT GC6 1840` under R1 framing (superseded).
> [R1] Under R1, object `GC6` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `148|OBJ HK9 -|532` carried the object record `OBJ HK9 -` under R1 framing (superseded).
> [R1] frame `149|HIT HK9 1877|712` carried the weight record `HIT HK9 1877` under R1 framing (superseded).
> [R1] Under R1, object `HK9` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `149|OBJ JSC ZXK|760` carried the object record `OBJ JSC ZXK` under R1 framing (superseded).
> [R1] frame `150|HIT JSC 1914|724` carried the weight record `HIT JSC 1914` under R1 framing (superseded).
> [R1] Under R1, object `JSC` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `150|OBJ KZF A4N|713` carried the object record `OBJ KZF A4N` under R1 framing (superseded).
> [R1] frame `151|HIT KZF 1951|736` carried the weight record `HIT KZF 1951` under R1 framing (superseded).
> [R1] Under R1, object `KZF` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `151|OBJ L6J BBR,BBR|959` carried the object record `OBJ L6J BBR,BBR` under R1 framing (superseded).
> [R1] frame `152|HIT L6J 1988|715` carried the weight record `HIT L6J 1988` under R1 framing (superseded).
> [R1] Under R1, object `L6J` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `152|OBJ MDM -|550` carried the object record `OBJ MDM -` under R1 framing (superseded).
> [R1] frame `153|HIT MDM 2025|716` carried the weight record `HIT MDM 2025` under R1 framing (superseded).
> [R1] Under R1, object `MDM` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `153|OBJ NLQ DRX|756` carried the object record `OBJ NLQ DRX` under R1 framing (superseded).
> [R1] frame `154|HIT NLQ 2062|730` carried the weight record `HIT NLQ 2062` under R1 framing (superseded).
> [R1] Under R1, object `NLQ` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `154|OBJ PTT EY0,EY0|987` carried the object record `OBJ PTT EY0,EY0` under R1 framing (superseded).
> [R1] frame `155|HIT PTT 2099|753` carried the weight record `HIT PTT 2099` under R1 framing (superseded).
> [R1] Under R1, object `PTT` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `155|OBJ Q0W F53|673` carried the object record `OBJ Q0W F53` under R1 framing (superseded).
> [R1] frame `156|HIT Q0W 2136|713` carried the weight record `HIT Q0W 2136` under R1 framing (superseded).
> [R1] Under R1, object `Q0W` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `156|OBJ R7Z -|555` carried the object record `OBJ R7Z -` under R1 framing (superseded).
> [R1] frame `157|HIT R7Z 2173|725` carried the weight record `HIT R7Z 2173` under R1 framing (superseded).
> [R1] Under R1, object `R7Z` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `157|OBJ SE2 HK9,HK9|937` carried the object record `OBJ SE2 HK9,HK9` under R1 framing (superseded).
> [R1] frame `158|HIT SE2 2210|692` carried the weight record `HIT SE2 2210` under R1 framing (superseded).
> [R1] Under R1, object `SE2` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `158|OBJ TM5 JSC|721` carried the object record `OBJ TM5 JSC` under R1 framing (superseded).
> [R1] frame `159|HIT TM5 2247|714` carried the weight record `HIT TM5 2247` under R1 framing (superseded).
> [R1] Under R1, object `TM5` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `159|OBJ UU8 KZF|744` carried the object record `OBJ UU8 KZF` under R1 framing (superseded).
> [R1] frame `160|HIT UU8 2284|727` carried the weight record `HIT UU8 2284` under R1 framing (superseded).
> [R1] Under R1, object `UU8` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `160|OBJ V1B -|529` carried the object record `OBJ V1B -` under R1 framing (superseded).
> [R1] frame `161|HIT V1B 2321|694` carried the weight record `HIT V1B 2321` under R1 framing (superseded).
> [R1] Under R1, object `V1B` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `161|OBJ W8E MDM|717` carried the object record `OBJ W8E MDM` under R1 framing (superseded).
> [R1] frame `162|HIT W8E 2358|715` carried the weight record `HIT W8E 2358` under R1 framing (superseded).
> [R1] Under R1, object `W8E` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `162|OBJ XFH NLQ|748` carried the object record `OBJ XFH NLQ` under R1 framing (superseded).
> [R1] frame `163|HIT XFH 2395|734` carried the weight record `HIT XFH 2395` under R1 framing (superseded).
> [R1] Under R1, object `XFH` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `163|OBJ YNL PTT,PTT|1066` carried the object record `OBJ YNL PTT,PTT` under R1 framing (superseded).
> [R1] frame `164|HIT YNL 2432|739` carried the weight record `HIT YNL 2432` under R1 framing (superseded).
> [R1] Under R1, object `YNL` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `164|OBJ ZVP -|584` carried the object record `OBJ ZVP -` under R1 framing (superseded).
> [R1] frame `165|HIT ZVP 2469|762` carried the weight record `HIT ZVP 2469` under R1 framing (superseded).
> [R1] Under R1, object `ZVP` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `165|OBJ A2S R7Z|708` carried the object record `OBJ A2S R7Z` under R1 framing (superseded).
> [R1] frame `166|HIT A2S 2506|696` carried the weight record `HIT A2S 2506` under R1 framing (superseded).
> [R1] Under R1, object `A2S` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `166|OBJ B9V SE2,SE2|940` carried the object record `OBJ B9V SE2,SE2` under R1 framing (superseded).
> [R1] frame `167|HIT B9V 2543|708` carried the weight record `HIT B9V 2543` under R1 framing (superseded).
> [R1] Under R1, object `B9V` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `167|OBJ CGY TM5|724` carried the object record `OBJ CGY TM5` under R1 framing (superseded).
> [R1] frame `168|HIT CGY 2580|727` carried the weight record `HIT CGY 2580` under R1 framing (superseded).
> [R1] Under R1, object `CGY` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `168|OBJ DP1 -|525` carried the object record `OBJ DP1 -` under R1 framing (superseded).
> [R1] frame `169|HIT DP1 2617|698` carried the weight record `HIT DP1 2617` under R1 framing (superseded).
> [R1] Under R1, object `DP1` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `169|OBJ EW4 V1B,V1B|937` carried the object record `OBJ EW4 V1B,V1B` under R1 framing (superseded).
> [R1] frame `170|HIT EW4 2654|710` carried the weight record `HIT EW4 2654` under R1 framing (superseded).
> [R1] Under R1, object `EW4` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `170|OBJ F37 W8E|671` carried the object record `OBJ F37 W8E` under R1 framing (superseded).
> [R1] frame `171|HIT F37 2691|679` carried the weight record `HIT F37 2691` under R1 framing (superseded).
> [R1] Under R1, object `F37` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R1] frame `171|OBJ GAA XFH|714` carried the object record `OBJ GAA XFH` under R1 framing (superseded).
> [R1] frame `172|HIT GAA 2728|705` carried the weight record `HIT GAA 2728` under R1 framing (superseded).
> [R1] Under R1, object `GAA` was reconciled by the no join (records stood alone) and ordered with a tie-break by file order, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.

### R2 decommissioned examples

The following R2 frames use the tab-delimited, base32 payload, additive checksum envelope. Every one is superseded; they are shown so that the historical shape is on record and so that a reader who greps for record keywords sees the superseded era in bulk. Do not port any of these to R5.

> [R2] frame `200	J5BEUICRGJJSALI=	542` carried the object record `OBJ Q2S -` under R2 framing (superseded).
> [R2] frame `201	JBEVIICRGJJSAMRQGI======	655` carried the weight record `HIT Q2S 202` under R2 framing (superseded).
> [R2] Under R2, object `Q2S` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `201	J5BEUICSHFLCAU2KKU======	750` carried the object record `OBJ R9V SJU` under R2 framing (superseded).
> [R2] frame `202	JBEVIICSHFLCAMRTHE======	676` carried the weight record `HIT R9V 239` under R2 framing (superseded).
> [R2] Under R2, object `R9V` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `202	J5BEUICTI5MSAVCSLA======	780` carried the object record `OBJ SGY TRX` under R2 framing (superseded).
> [R2] frame `203	JBEVIICTI5MSAMRXGY======	695` carried the weight record `HIT SGY 276` under R2 framing (superseded).
> [R2] Under R2, object `SGY` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `203	J5BEUICUKAYSAVKZGAWFCNCO	973` carried the object record `OBJ TP1 UY0,Q4N` under R2 framing (superseded).
> [R2] frame `204	JBEVIICUKAYSAMZRGM======	657` carried the weight record `HIT TP1 313` under R2 framing (superseded).
> [R2] Under R2, object `TP1` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `204	J5BEUICVK42CALI=	552` carried the object record `OBJ UW4 -` under R2 framing (superseded).
> [R2] frame `205	JBEVIICVK42CAMZVGA======	669` carried the weight record `HIT UW4 350` under R2 framing (superseded).
> [R2] Under R2, object `UW4` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `205	J5BEUICWGM3SAV2DGY======	683` carried the object record `OBJ V37 WC6` under R2 framing (superseded).
> [R2] frame `206	JBEVIICWGM3SAMZYG4======	647` carried the weight record `HIT V37 387` under R2 framing (superseded).
> [R2] Under R2, object `V37` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `206	J5BEUICXIFASAWCLHEWFIUSY	1018` carried the object record `OBJ WAA XK9,TRX` under R2 framing (superseded).
> [R2] frame `207	JBEVIICXIFASANBSGQ======	664` carried the weight record `HIT WAA 424` under R2 framing (superseded).
> [R2] Under R2, object `WAA` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `207	J5BEUICYJBCCAWKTIM======	750` carried the object record `OBJ XHD YSC` under R2 framing (superseded).
> [R2] frame `208	JBEVIICYJBCCANBWGE======	676` carried the weight record `HIT XHD 461` under R2 framing (superseded).
> [R2] Under R2, object `XHD` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `208	J5BEUICZKFDSALI=	569` carried the object record `OBJ YQG -` under R2 framing (superseded).
> [R2] frame `209	JBEVIICZKFDSANBZHA======	699` carried the weight record `HIT YQG 498` under R2 framing (superseded).
> [R2] Under R2, object `YQG` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `209	J5BEUIC2LBFSAQJWJIWFOQZW	981` carried the object record `OBJ ZXK A6J,WC6` under R2 framing (superseded).
> [R2] frame `210	JBEVIIC2LBFSANJTGU======	703` carried the weight record `HIT ZXK 535` under R2 framing (superseded).
> [R2] Under R2, object `ZXK` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `210	J5BEUICBGRHCAQSEJU======	689` carried the object record `OBJ A4N BDM` under R2 framing (superseded).
> [R2] frame `211	JBEVIICBGRHCANJXGI======	646` carried the weight record `HIT A4N 572` under R2 framing (superseded).
> [R2] Under R2, object `A4N` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `211	J5BEUICCIJJCAQ2MKE======	721` carried the object record `OBJ BBR CLQ` under R2 framing (superseded).
> [R2] frame `212	JBEVIICCIJJCANRQHE======	666` carried the weight record `HIT BBR 609` under R2 framing (superseded).
> [R2] Under R2, object `BBR` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `212	J5BEUICDJJKSALI=	554` carried the object record `OBJ CJU -` under R2 framing (superseded).
> [R2] frame `213	JBEVIICDJJKSANRUGY======	679` carried the weight record `HIT CJU 646` under R2 framing (superseded).
> [R2] Under R2, object `CJU` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `213	J5BEUICEKJMCARJQK4======	725` carried the object record `OBJ DRX E0W` under R2 framing (superseded).
> [R2] frame `214	JBEVIICEKJMCANRYGM======	692` carried the weight record `HIT DRX 683` under R2 framing (superseded).
> [R2] Under R2, object `DRX` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `214	J5BEUICFLEYCARRXLI======	704` carried the object record `OBJ EY0 F7Z` under R2 framing (superseded).
> [R2] frame `215	JBEVIICFLEYCANZSGA======	652` carried the weight record `HIT EY0 720` under R2 framing (superseded).
> [R2] Under R2, object `EY0` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `215	J5BEUICGGUZSAR2FGIWEGTCR	915` carried the object record `OBJ F53 GE2,CLQ` under R2 framing (superseded).
> [R2] frame `216	JBEVIICGGUZSANZVG4======	630` carried the weight record `HIT F53 757` under R2 framing (superseded).
> [R2] Under R2, object `F53` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `216	J5BEUICHIM3CALI=	520` carried the object record `OBJ GC6 -` under R2 framing (superseded).
> [R2] frame `217	JBEVIICHIM3CANZZGQ======	649` carried the weight record `HIT GC6 794` under R2 framing (superseded).
> [R2] Under R2, object `GC6` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `217	J5BEUICIJM4SASSVHA======	702` carried the object record `OBJ HK9 JU8` under R2 framing (superseded).
> [R2] frame `218	JBEVIICIJM4SAOBTGE======	653` carried the weight record `HIT HK9 831` under R2 framing (superseded).
> [R2] Under R2, object `HK9` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `218	J5BEUICKKNBSASZRIIWEMN22	956` carried the object record `OBJ JSC K1B,F7Z` under R2 framing (superseded).
> [R2] frame `219	JBEVIICKKNBSAOBWHA======	683` carried the weight record `HIT JSC 868` under R2 framing (superseded).
> [R2] Under R2, object `JSC` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `219	J5BEUICLLJDCATBYIU======	719` carried the object record `OBJ KZF L8E` under R2 framing (superseded).
> [R2] frame `220	JBEVIICLLJDCAOJQGU======	686` carried the weight record `HIT KZF 905` under R2 framing (superseded).
> [R2] Under R2, object `KZF` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `220	J5BEUICMGZFCALI=	532` carried the object record `OBJ L6J -` under R2 framing (superseded).
> [R2] frame `221	JBEVIICMGZFCAOJUGI======	656` carried the weight record `HIT L6J 942` under R2 framing (superseded).
> [R2] Under R2, object `L6J` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `221	J5BEUICNIRGSATSOJQWEUVJY	996` carried the object record `OBJ MDM NNL,JU8` under R2 framing (superseded).
> [R2] frame `222	JBEVIICNIRGSAOJXHE======	684` carried the weight record `HIT MDM 979` under R2 framing (superseded).
> [R2] Under R2, object `MDM` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `222	J5BEUICOJRISAUCWKA======	764` carried the object record `OBJ NLQ PVP` under R2 framing (superseded).
> [R2] frame `223	JBEVIICOJRISAMJQGE3A====	728` carried the weight record `HIT NLQ 1016` under R2 framing (superseded).
> [R2] Under R2, object `NLQ` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `223	J5BEUICQKRKCAUJSKM======	745` carried the object record `OBJ PTT Q2S` under R2 framing (superseded).
> [R2] frame `224	JBEVIICQKRKCAMJQGUZQ====	742` carried the weight record `HIT PTT 1053` under R2 framing (superseded).
> [R2] Under R2, object `PTT` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `224	J5BEUICRGBLSALI=	544` carried the object record `OBJ Q0W -` under R2 framing (superseded).
> [R2] frame `225	JBEVIICRGBLSAMJQHEYA====	711` carried the weight record `HIT Q0W 1090` under R2 framing (superseded).
> [R2] Under R2, object `Q0W` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `225	J5BEUICSG5NCAU2HLE======	753` carried the object record `OBJ R7Z SGY` under R2 framing (superseded).
> [R2] frame `226	JBEVIICSG5NCAMJRGI3Q====	723` carried the weight record `HIT R7Z 1127` under R2 framing (superseded).
> [R2] Under R2, object `R7Z` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `226	J5BEUICTIUZCAVCQGE======	698` carried the object record `OBJ SE2 TP1` under R2 framing (superseded).
> [R2] frame `227	JBEVIICTIUZCAMJRGY2A====	699` carried the weight record `HIT SE2 1164` under R2 framing (superseded).
> [R2] Under R2, object `SE2` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `227	J5BEUICUJU2SAVKXGQWFCMST	979` carried the object record `OBJ TM5 UW4,Q2S` under R2 framing (superseded).
> [R2] frame `228	JBEVIICUJU2SAMJSGAYQ====	703` carried the weight record `HIT TM5 1201` under R2 framing (superseded).
> [R2] Under R2, object `TM5` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `228	J5BEUICVKU4CALI=	554` carried the object record `OBJ UU8 -` under R2 framing (superseded).
> [R2] frame `229	JBEVIICVKU4CAMJSGM4A====	725` carried the weight record `HIT UU8 1238` under R2 framing (superseded).
> [R2] Under R2, object `UU8` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `229	J5BEUICWGFBCAV2BIE======	701` carried the object record `OBJ V1B WAA` under R2 framing (superseded).
> [R2] frame `230	JBEVIICWGFBCAMJSG42Q====	701` carried the weight record `HIT V1B 1275` under R2 framing (superseded).
> [R2] Under R2, object `V1B` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `230	J5BEUICXHBCSAWCIIQWFIUBR	980` carried the object record `OBJ W8E XHD,TP1` under R2 framing (superseded).
> [R2] frame `231	JBEVIICXHBCSAMJTGEZA====	704` carried the weight record `HIT W8E 1312` under R2 framing (superseded).
> [R2] Under R2, object `W8E` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `231	J5BEUICYIZECAWKRI4======	754` carried the object record `OBJ XFH YQG` under R2 framing (superseded).
> [R2] frame `232	JBEVIICYIZECAMJTGQ4Q====	732` carried the weight record `HIT XFH 1349` under R2 framing (superseded).
> [R2] Under R2, object `XFH` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `232	J5BEUICZJZGCALI=	571` carried the object record `OBJ YNL -` under R2 framing (superseded).
> [R2] frame `233	JBEVIICZJZGCAMJTHA3A====	746` carried the weight record `HIT YNL 1386` under R2 framing (superseded).
> [R2] Under R2, object `YNL` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `233	J5BEUIC2KZICAQJUJYWFOQKB	995` carried the object record `OBJ ZVP A4N,WAA` under R2 framing (superseded).
> [R2] frame `234	JBEVIIC2KZICAMJUGIZQ====	751` carried the weight record `HIT ZVP 1423` under R2 framing (superseded).
> [R2] Under R2, object `ZVP` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `234	J5BEUICBGJJSAQSCKI======	695` carried the object record `OBJ A2S BBR` under R2 framing (superseded).
> [R2] frame `235	JBEVIICBGJJSAMJUGYYA====	694` carried the weight record `HIT A2S 1460` under R2 framing (superseded).
> [R2] Under R2, object `A2S` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `235	J5BEUICCHFLCAQ2KKU======	718` carried the object record `OBJ B9V CJU` under R2 framing (superseded).
> [R2] frame `236	JBEVIICCHFLCAMJUHE3Q====	715` carried the weight record `HIT B9V 1497` under R2 framing (superseded).
> [R2] Under R2, object `B9V` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `236	J5BEUICDI5MSALI=	555` carried the object record `OBJ CGY -` under R2 framing (superseded).
> [R2] frame `237	JBEVIICDI5MSAMJVGM2A====	725` carried the weight record `HIT CGY 1534` under R2 framing (superseded).
> [R2] Under R2, object `CGY` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `237	J5BEUICEKAYSARKZGA======	686` carried the object record `OBJ DP1 EY0` under R2 framing (superseded).
> [R2] frame `238	JBEVIICEKAYSAMJVG4YQ====	696` carried the weight record `HIT DP1 1571` under R2 framing (superseded).
> [R2] Under R2, object `DP1` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `238	J5BEUICFK42CARRVGM======	665` carried the object record `OBJ EW4 F53` under R2 framing (superseded).
> [R2] frame `239	JBEVIICFK42CAMJWGA4A====	708` carried the weight record `HIT EW4 1608` under R2 framing (superseded).
> [R2] Under R2, object `EW4` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `239	J5BEUICGGM3SAR2DGYWEGSSV	921` carried the object record `OBJ F37 GC6,CJU` under R2 framing (superseded).
> [R2] frame `240	JBEVIICGGM3SAMJWGQ2Q====	677` carried the weight record `HIT F37 1645` under R2 framing (superseded).
> [R2] Under R2, object `F37` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `240	J5BEUICHIFASALI=	529` carried the object record `OBJ GAA -` under R2 framing (superseded).
> [R2] frame `241	JBEVIICHIFASAMJWHAZA====	703` carried the weight record `HIT GAA 1682` under R2 framing (superseded).
> [R2] Under R2, object `GAA` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `241	J5BEUICIJBCCASSTIM======	719` carried the object record `OBJ HHD JSC` under R2 framing (superseded).
> [R2] frame `242	JBEVIICIJBCCAMJXGE4Q====	715` carried the weight record `HIT HHD 1719` under R2 framing (superseded).
> [R2] Under R2, object `HHD` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `242	J5BEUICKKFDSAS22IYWEMNJT	962` carried the object record `OBJ JQG KZF,F53` under R2 framing (superseded).
> [R2] frame `243	JBEVIICKKFDSAMJXGU3A====	730` carried the weight record `HIT JQG 1756` under R2 framing (superseded).
> [R2] Under R2, object `JQG` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `243	J5BEUICLLBFSATBWJI======	725` carried the object record `OBJ KXK L6J` under R2 framing (superseded).
> [R2] frame `244	JBEVIICLLBFSAMJXHEZQ====	743` carried the weight record `HIT KXK 1793` under R2 framing (superseded).
> [R2] Under R2, object `KXK` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `244	J5BEUICMGRHCALI=	534` carried the object record `OBJ L4N -` under R2 framing (superseded).
> [R2] frame `245	JBEVIICMGRHCAMJYGMYA====	703` carried the weight record `HIT L4N 1830` under R2 framing (superseded).
> [R2] Under R2, object `L4N` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `245	J5BEUICNIJJCATSMKEWEUU2D	1011` carried the object record `OBJ MBR NLQ,JSC` under R2 framing (superseded).
> [R2] frame `246	JBEVIICNIJJCAMJYGY3Q====	732` carried the weight record `HIT MBR 1867` under R2 framing (superseded).
> [R2] Under R2, object `MBR` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `246	J5BEUICOJJKSAUCUKQ======	768` carried the object record `OBJ NJU PTT` under R2 framing (superseded).
> [R2] frame `247	JBEVIICOJJKSAMJZGA2A====	736` carried the weight record `HIT NJU 1904` under R2 framing (superseded).
> [R2] Under R2, object `NJU` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `247	J5BEUICQKJMCAUJQK4======	749` carried the object record `OBJ PRX Q0W` under R2 framing (superseded).
> [R2] frame `248	JBEVIICQKJMCAMJZGQYQ====	750` carried the weight record `HIT PRX 1941` under R2 framing (superseded).
> [R2] Under R2, object `PRX` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `248	J5BEUICRLEYCALI=	546` carried the object record `OBJ QY0 -` under R2 framing (superseded).
> [R2] frame `249	JBEVIICRLEYCAMJZG44A====	728` carried the weight record `HIT QY0 1978` under R2 framing (superseded).
> [R2] Under R2, object `QY0` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `249	J5BEUICSGUZSAU2FGI======	671` carried the object record `OBJ R53 SE2` under R2 framing (superseded).
> [R2] frame `250	JBEVIICSGUZSAMRQGE2Q====	679` carried the weight record `HIT R53 2015` under R2 framing (superseded).
> [R2] Under R2, object `R53` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `250	J5BEUICTIM3CAVCNGU======	701` carried the object record `OBJ SC6 TM5` under R2 framing (superseded).
> [R2] frame `251	JBEVIICTIM3CAMRQGUZA====	698` carried the weight record `HIT SC6 2052` under R2 framing (superseded).
> [R2] Under R2, object `SC6` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `251	J5BEUICUJM4SAVKVHAWFCMCX	985` carried the object record `OBJ TK9 UU8,Q0W` under R2 framing (superseded).
> [R2] frame `252	JBEVIICUJM4SAMRQHA4Q====	720` carried the weight record `HIT TK9 2089` under R2 framing (superseded).
> [R2] Under R2, object `TK9` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `252	J5BEUICVKNBSALI=	563` carried the object record `OBJ USC -` under R2 framing (superseded).
> [R2] frame `253	JBEVIICVKNBSAMRRGI3A====	731` carried the weight record `HIT USC 2126` under R2 framing (superseded).
> [R2] Under R2, object `USC` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `253	J5BEUICWLJDCAVZYIU======	741` carried the object record `OBJ VZF W8E` under R2 framing (superseded).
> [R2] frame `254	JBEVIICWLJDCAMRRGYZQ====	743` carried the weight record `HIT VZF 2163` under R2 framing (superseded).
> [R2] Under R2, object `VZF` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `254	J5BEUICXGZFCAWCGJAWFITJV	986` carried the object record `OBJ W6J XFH,TM5` under R2 framing (superseded).
> [R2] frame `255	JBEVIICXGZFCAMRSGAYA====	704` carried the weight record `HIT W6J 2200` under R2 framing (superseded).
> [R2] Under R2, object `W6J` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `255	J5BEUICYIRGSAWKOJQ======	759` carried the object record `OBJ XDM YNL` under R2 framing (superseded).
> [R2] frame `256	JBEVIICYIRGSAMRSGM3Q====	732` carried the weight record `HIT XDM 2237` under R2 framing (superseded).
> [R2] Under R2, object `XDM` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `256	J5BEUICZJRISALI=	574` carried the object record `OBJ YLQ -` under R2 framing (superseded).
> [R2] frame `257	JBEVIICZJRISAMRSG42A====	746` carried the weight record `HIT YLQ 2274` under R2 framing (superseded).
> [R2] Under R2, object `YLQ` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `257	J5BEUIC2KRKCAQJSKMWFOOCF	995` carried the object record `OBJ ZTT A2S,W8E` under R2 framing (superseded).
> [R2] frame `258	JBEVIIC2KRKCAMRTGEYQ====	750` carried the weight record `HIT ZTT 2311` under R2 framing (superseded).
> [R2] Under R2, object `ZTT` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `258	J5BEUICBGBLSAQRZKY======	692` carried the object record `OBJ A0W B9V` under R2 framing (superseded).
> [R2] frame `259	JBEVIICBGBLSAMRTGQ4A====	702` carried the weight record `HIT A0W 2348` under R2 framing (superseded).
> [R2] Under R2, object `A0W` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `259	J5BEUICCG5NCAQ2HLE======	721` carried the object record `OBJ B7Z CGY` under R2 framing (superseded).
> [R2] frame `260	JBEVIICCG5NCAMRTHA2Q====	714` carried the weight record `HIT B7Z 2385` under R2 framing (superseded).
> [R2] Under R2, object `B7Z` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `260	J5BEUICDIUZCALI=	514` carried the object record `OBJ CE2 -` under R2 framing (superseded).
> [R2] frame `261	JBEVIICDIUZCAMRUGIZA====	681` carried the weight record `HIT CE2 2422` under R2 framing (superseded).
> [R2] Under R2, object `CE2` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `261	J5BEUICEJU2SARKXGQ======	689` carried the object record `OBJ DM5 EW4` under R2 framing (superseded).
> [R2] frame `262	JBEVIICEJU2SAMRUGU4Q====	703` carried the weight record `HIT DM5 2459` under R2 framing (superseded).
> [R2] Under R2, object `DM5` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `262	J5BEUICFKU4CARRTG4======	669` carried the object record `OBJ EU8 F37` under R2 framing (superseded).
> [R2] frame `263	JBEVIICFKU4CAMRUHE3A====	716` carried the weight record `HIT EU8 2496` under R2 framing (superseded).
> [R2] Under R2, object `EU8` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `263	J5BEUICGGFBCAR2BIEWEGR2Z	940` carried the object record `OBJ F1B GAA,CGY` under R2 framing (superseded).
> [R2] frame `264	JBEVIICGGFBCAMRVGMZQ====	683` carried the weight record `HIT F1B 2533` under R2 framing (superseded).
> [R2] Under R2, object `F1B` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `264	J5BEUICHHBCSALI=	524` carried the object record `OBJ G8E -` under R2 framing (superseded).
> [R2] frame `265	JBEVIICHHBCSAMRVG4YA====	695` carried the weight record `HIT G8E 2570` under R2 framing (superseded).
> [R2] Under R2, object `G8E` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `265	J5BEUICIIZECASSRI4======	723` carried the object record `OBJ HFH JQG` under R2 framing (superseded).
> [R2] frame `266	JBEVIICIIZECAMRWGA3Q====	714` carried the weight record `HIT HFH 2607` under R2 framing (superseded).
> [R2] Under R2, object `HFH` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `266	J5BEUICKJZGCAS2YJMWEMMZX	969` carried the object record `OBJ JNL KXK,F37` under R2 framing (superseded).
> [R2] frame `267	JBEVIICKJZGCAMRWGQ2A====	729` carried the weight record `HIT JNL 2644` under R2 framing (superseded).
> [R2] Under R2, object `JNL` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `267	J5BEUICLKZICATBUJY======	730` carried the object record `OBJ KVP L4N` under R2 framing (superseded).
> [R2] frame `268	JBEVIICLKZICAMRWHAYQ====	743` carried the weight record `HIT KVP 2681` under R2 framing (superseded).
> [R2] Under R2, object `KVP` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `268	J5BEUICMGJJSALI=	537` carried the object record `OBJ L2S -` under R2 framing (superseded).
> [R2] frame `269	JBEVIICMGJJSAMRXGE4A====	712` carried the weight record `HIT L2S 2718` under R2 framing (superseded).
> [R2] Under R2, object `L2S` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `269	J5BEUICNHFLCATSKKUWEUUKH	1010` carried the object record `OBJ M9V NJU,JQG` under R2 framing (superseded).
> [R2] frame `270	JBEVIICNHFLCAMRXGU2Q====	724` carried the weight record `HIT M9V 2755` under R2 framing (superseded).
> [R2] Under R2, object `M9V` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `270	J5BEUICOI5MSAUCSLA======	771` carried the object record `OBJ NGY PRX` under R2 framing (superseded).
> [R2] frame `271	JBEVIICOI5MSAMRXHEZA====	743` carried the weight record `HIT NGY 2792` under R2 framing (superseded).
> [R2] Under R2, object `NGY` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R2] frame `271	J5BEUICQKAYSAUKZGA======	710` carried the object record `OBJ PP1 QY0` under R2 framing (superseded).
> [R2] frame `272	JBEVIICQKAYSAMRYGI4Q====	715` carried the weight record `HIT PP1 2829` under R2 framing (superseded).
> [R2] Under R2, object `PP1` was reconciled by the outer join (weightless objects defaulted to 0) and ordered with a tie-break by ascending key, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.

### R3 decommissioned examples

The following R3 frames use the space-delimited, hex payload, MD5 prefix envelope. Every one is superseded; they are shown so that the historical shape is on record and so that a reader who greps for record keywords sees the superseded era in bulk. Do not port any of these to R5.

> [R3] frame `300 4f424a20584648202d md5:00000000` carried the object record `OBJ XFH -` under R3 framing (superseded).
> [R3] frame `301 4849542058464820333033 md5:00000000` carried the weight record `HIT XFH 303` under R3 framing (superseded).
> [R3] Under R3, object `XFH` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `301 4f424a20594e4c204b3142 md5:9e3779b1` carried the object record `OBJ YNL K1B` under R3 framing (superseded).
> [R3] frame `302 48495420594e4c20333430 md5:00009e37` carried the weight record `HIT YNL 340` under R3 framing (superseded).
> [R3] Under R3, object `YNL` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `302 4f424a205a5650204c3845 md5:3c6ef362` carried the object record `OBJ ZVP L8E` under R3 framing (superseded).
> [R3] frame `303 484954205a565020333737 md5:00013c6e` carried the weight record `HIT ZVP 377` under R3 framing (superseded).
> [R3] Under R3, object `ZVP` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `303 4f424a20413253204d46482c445454 md5:daa66d13` carried the object record `OBJ A2S MFH,DTT` under R3 framing (superseded).
> [R3] frame `304 4849542041325320343134 md5:0001daa5` carried the weight record `HIT A2S 414` under R3 framing (superseded).
> [R3] Under R3, object `A2S` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `304 4f424a20423956202d md5:78dde6c4` carried the object record `OBJ B9V -` under R3 framing (superseded).
> [R3] frame `305 4849542042395620343531 md5:000278dc` carried the weight record `HIT B9V 451` under R3 framing (superseded).
> [R3] Under R3, object `B9V` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `305 4f424a2043475920505650 md5:17156075` carried the object record `OBJ CGY PVP` under R3 framing (superseded).
> [R3] frame `306 4849542043475920343838 md5:00031713` carried the weight record `HIT CGY 488` under R3 framing (superseded).
> [R3] Under R3, object `CGY` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `306 4f424a20445031205132532c474532 md5:b54cda26` carried the object record `OBJ DP1 Q2S,GE2` under R3 framing (superseded).
> [R3] frame `307 4849542044503120353235 md5:0003b54a` carried the weight record `HIT DP1 525` under R3 framing (superseded).
> [R3] Under R3, object `DP1` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `307 4f424a2045573420523956 md5:538453d7` carried the object record `OBJ EW4 R9V` under R3 framing (superseded).
> [R3] frame `308 4849542045573420353632 md5:00045381` carried the weight record `HIT EW4 562` under R3 framing (superseded).
> [R3] Under R3, object `EW4` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `308 4f424a20463337202d md5:f1bbcd88` carried the object record `OBJ F37 -` under R3 framing (superseded).
> [R3] frame `309 4849542046333720353939 md5:0004f1b8` carried the weight record `HIT F37 599` under R3 framing (superseded).
> [R3] Under R3, object `F37` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `309 4f424a20474141205450312c4b3142 md5:8ff34739` carried the object record `OBJ GAA TP1,K1B` under R3 framing (superseded).
> [R3] frame `310 4849542047414120363336 md5:00058fef` carried the weight record `HIT GAA 636` under R3 framing (superseded).
> [R3] Under R3, object `GAA` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `310 4f424a2048484420555734 md5:2e2ac0ea` carried the object record `OBJ HHD UW4` under R3 framing (superseded).
> [R3] frame `311 4849542048484420363733 md5:00062e26` carried the weight record `HIT HHD 673` under R3 framing (superseded).
> [R3] Under R3, object `HHD` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `311 4f424a204a514720563337 md5:cc623a9b` carried the object record `OBJ JQG V37` under R3 framing (superseded).
> [R3] frame `312 484954204a514720373130 md5:0006cc5d` carried the weight record `HIT JQG 710` under R3 framing (superseded).
> [R3] Under R3, object `JQG` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `312 4f424a204b584b202d md5:6a99b44c` carried the object record `OBJ KXK -` under R3 framing (superseded).
> [R3] frame `313 484954204b584b20373437 md5:00076a94` carried the weight record `HIT KXK 747` under R3 framing (superseded).
> [R3] Under R3, object `KXK` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `313 4f424a204c344e20584844 md5:08d12dfd` carried the object record `OBJ L4N XHD` under R3 framing (superseded).
> [R3] frame `314 484954204c344e20373834 md5:000808cb` carried the weight record `HIT L4N 784` under R3 framing (superseded).
> [R3] Under R3, object `L4N` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `314 4f424a204d425220595147 md5:a708a7ae` carried the object record `OBJ MBR YQG` under R3 framing (superseded).
> [R3] frame `315 484954204d425220383231 md5:0008a702` carried the weight record `HIT MBR 821` under R3 framing (superseded).
> [R3] Under R3, object `MBR` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `315 4f424a204e4a55205a584b2c523956 md5:4540215f` carried the object record `OBJ NJU ZXK,R9V` under R3 framing (superseded).
> [R3] frame `316 484954204e4a5520383538 md5:00094539` carried the weight record `HIT NJU 858` under R3 framing (superseded).
> [R3] Under R3, object `NJU` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `316 4f424a20505258202d md5:e3779b10` carried the object record `OBJ PRX -` under R3 framing (superseded).
> [R3] frame `317 4849542050525820383935 md5:0009e370` carried the weight record `HIT PRX 895` under R3 framing (superseded).
> [R3] Under R3, object `PRX` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `317 4f424a2051593020424252 md5:81af14c1` carried the object record `OBJ QY0 BBR` under R3 framing (superseded).
> [R3] frame `318 4849542051593020393332 md5:000a81a7` carried the weight record `HIT QY0 932` under R3 framing (superseded).
> [R3] Under R3, object `QY0` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `318 4f424a2052353320434a552c555734 md5:1fe68e72` carried the object record `OBJ R53 CJU,UW4` under R3 framing (superseded).
> [R3] frame `319 4849542052353320393639 md5:000b1fde` carried the weight record `HIT R53 969` under R3 framing (superseded).
> [R3] Under R3, object `R53` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `319 4f424a2053433620445258 md5:be1e0823` carried the object record `OBJ SC6 DRX` under R3 framing (superseded).
> [R3] frame `320 484954205343362031303036 md5:000bbe15` carried the weight record `HIT SC6 1006` under R3 framing (superseded).
> [R3] Under R3, object `SC6` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `320 4f424a20544b39202d md5:5c5581d4` carried the object record `OBJ TK9 -` under R3 framing (superseded).
> [R3] frame `321 48495420544b392031303433 md5:000c5c4c` carried the weight record `HIT TK9 1043` under R3 framing (superseded).
> [R3] Under R3, object `TK9` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `321 4f424a20555343204635332c584844 md5:fa8cfb85` carried the object record `OBJ USC F53,XHD` under R3 framing (superseded).
> [R3] frame `322 484954205553432031303830 md5:000cfa83` carried the weight record `HIT USC 1080` under R3 framing (superseded).
> [R3] Under R3, object `USC` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `322 4f424a20565a4620474336 md5:98c47536` carried the object record `OBJ VZF GC6` under R3 framing (superseded).
> [R3] frame `323 48495420565a462031313137 md5:000d98ba` carried the weight record `HIT VZF 1117` under R3 framing (superseded).
> [R3] Under R3, object `VZF` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `323 4f424a2057364a20484b39 md5:36fbeee7` carried the object record `OBJ W6J HK9` under R3 framing (superseded).
> [R3] frame `324 4849542057364a2031313534 md5:000e36f1` carried the weight record `HIT W6J 1154` under R3 framing (superseded).
> [R3] Under R3, object `W6J` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `324 4f424a2058444d202d md5:d5336898` carried the object record `OBJ XDM -` under R3 framing (superseded).
> [R3] frame `325 4849542058444d2031313931 md5:000ed528` carried the weight record `HIT XDM 1191` under R3 framing (superseded).
> [R3] Under R3, object `XDM` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `325 4f424a20594c51204b5a46 md5:736ae249` carried the object record `OBJ YLQ KZF` under R3 framing (superseded).
> [R3] frame `326 48495420594c512031323238 md5:000f735f` carried the weight record `HIT YLQ 1228` under R3 framing (superseded).
> [R3] Under R3, object `YLQ` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `326 4f424a205a5454204c364a md5:11a25bfa` carried the object record `OBJ ZTT L6J` under R3 framing (superseded).
> [R3] frame `327 484954205a54542031323635 md5:00101196` carried the weight record `HIT ZTT 1265` under R3 framing (superseded).
> [R3] Under R3, object `ZTT` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `327 4f424a20413057204d444d2c445258 md5:afd9d5ab` carried the object record `OBJ A0W MDM,DRX` under R3 framing (superseded).
> [R3] frame `328 484954204130572031333032 md5:0010afcd` carried the weight record `HIT A0W 1302` under R3 framing (superseded).
> [R3] Under R3, object `A0W` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `328 4f424a2042375a202d md5:4e114f5c` carried the object record `OBJ B7Z -` under R3 framing (superseded).
> [R3] frame `329 4849542042375a2031333339 md5:00114e04` carried the weight record `HIT B7Z 1339` under R3 framing (superseded).
> [R3] Under R3, object `B7Z` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `329 4f424a2043453220505454 md5:ec48c90d` carried the object record `OBJ CE2 PTT` under R3 framing (superseded).
> [R3] frame `330 484954204345322031333736 md5:0011ec3b` carried the weight record `HIT CE2 1376` under R3 framing (superseded).
> [R3] Under R3, object `CE2` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `330 4f424a20444d35205130572c474336 md5:8a8042be` carried the object record `OBJ DM5 Q0W,GC6` under R3 framing (superseded).
> [R3] frame `331 48495420444d352031343133 md5:00128a72` carried the weight record `HIT DM5 1413` under R3 framing (superseded).
> [R3] Under R3, object `DM5` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `331 4f424a204555382052375a md5:28b7bc6f` carried the object record `OBJ EU8 R7Z` under R3 framing (superseded).
> [R3] frame `332 484954204555382031343530 md5:001328a9` carried the weight record `HIT EU8 1450` under R3 framing (superseded).
> [R3] Under R3, object `EU8` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `332 4f424a20463142202d md5:c6ef3620` carried the object record `OBJ F1B -` under R3 framing (superseded).
> [R3] frame `333 484954204631422031343837 md5:0013c6e0` carried the weight record `HIT F1B 1487` under R3 framing (superseded).
> [R3] Under R3, object `F1B` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `333 4f424a2047384520544d352c4b5a46 md5:6526afd1` carried the object record `OBJ G8E TM5,KZF` under R3 framing (superseded).
> [R3] frame `334 484954204738452031353234 md5:00146517` carried the weight record `HIT G8E 1524` under R3 framing (superseded).
> [R3] Under R3, object `G8E` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `334 4f424a2048464820555538 md5:035e2982` carried the object record `OBJ HFH UU8` under R3 framing (superseded).
> [R3] frame `335 484954204846482031353631 md5:0015034e` carried the weight record `HIT HFH 1561` under R3 framing (superseded).
> [R3] Under R3, object `HFH` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `335 4f424a204a4e4c20563142 md5:a195a333` carried the object record `OBJ JNL V1B` under R3 framing (superseded).
> [R3] frame `336 484954204a4e4c2031353938 md5:0015a185` carried the weight record `HIT JNL 1598` under R3 framing (superseded).
> [R3] Under R3, object `JNL` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `336 4f424a204b5650202d md5:3fcd1ce4` carried the object record `OBJ KVP -` under R3 framing (superseded).
> [R3] frame `337 484954204b56502031363335 md5:00163fbc` carried the weight record `HIT KVP 1635` under R3 framing (superseded).
> [R3] Under R3, object `KVP` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `337 4f424a204c325320584648 md5:de049695` carried the object record `OBJ L2S XFH` under R3 framing (superseded).
> [R3] frame `338 484954204c32532031363732 md5:0016ddf3` carried the weight record `HIT L2S 1672` under R3 framing (superseded).
> [R3] Under R3, object `L2S` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `338 4f424a204d395620594e4c md5:7c3c1046` carried the object record `OBJ M9V YNL` under R3 framing (superseded).
> [R3] frame `339 484954204d39562031373039 md5:00177c2a` carried the weight record `HIT M9V 1709` under R3 framing (superseded).
> [R3] Under R3, object `M9V` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `339 4f424a204e4759205a56502c52375a md5:1a7389f7` carried the object record `OBJ NGY ZVP,R7Z` under R3 framing (superseded).
> [R3] frame `340 484954204e47592031373436 md5:00181a61` carried the weight record `HIT NGY 1746` under R3 framing (superseded).
> [R3] Under R3, object `NGY` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `340 4f424a20505031202d md5:b8ab03a8` carried the object record `OBJ PP1 -` under R3 framing (superseded).
> [R3] frame `341 484954205050312031373833 md5:0018b898` carried the weight record `HIT PP1 1783` under R3 framing (superseded).
> [R3] Under R3, object `PP1` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `341 4f424a2051573420423956 md5:56e27d59` carried the object record `OBJ QW4 B9V` under R3 framing (superseded).
> [R3] frame `342 484954205157342031383230 md5:001956cf` carried the weight record `HIT QW4 1820` under R3 framing (superseded).
> [R3] Under R3, object `QW4` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `342 4f424a20523337204347592c555538 md5:f519f70a` carried the object record `OBJ R37 CGY,UU8` under R3 framing (superseded).
> [R3] frame `343 484954205233372031383537 md5:0019f506` carried the weight record `HIT R37 1857` under R3 framing (superseded).
> [R3] Under R3, object `R37` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `343 4f424a2053414120445031 md5:935170bb` carried the object record `OBJ SAA DP1` under R3 framing (superseded).
> [R3] frame `344 484954205341412031383934 md5:001a933d` carried the weight record `HIT SAA 1894` under R3 framing (superseded).
> [R3] Under R3, object `SAA` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `344 4f424a20544844202d md5:3188ea6c` carried the object record `OBJ THD -` under R3 framing (superseded).
> [R3] frame `345 484954205448442031393331 md5:001b3174` carried the weight record `HIT THD 1931` under R3 framing (superseded).
> [R3] Under R3, object `THD` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `345 4f424a20555147204633372c584648 md5:cfc0641d` carried the object record `OBJ UQG F37,XFH` under R3 framing (superseded).
> [R3] frame `346 484954205551472031393638 md5:001bcfab` carried the weight record `HIT UQG 1968` under R3 framing (superseded).
> [R3] Under R3, object `UQG` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `346 4f424a2056584b20474141 md5:6df7ddce` carried the object record `OBJ VXK GAA` under R3 framing (superseded).
> [R3] frame `347 4849542056584b2032303035 md5:001c6de2` carried the weight record `HIT VXK 2005` under R3 framing (superseded).
> [R3] Under R3, object `VXK` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `347 4f424a2057344e20484844 md5:0c2f577f` carried the object record `OBJ W4N HHD` under R3 framing (superseded).
> [R3] frame `348 4849542057344e2032303432 md5:001d0c19` carried the weight record `HIT W4N 2042` under R3 framing (superseded).
> [R3] Under R3, object `W4N` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `348 4f424a20584252202d md5:aa66d130` carried the object record `OBJ XBR -` under R3 framing (superseded).
> [R3] frame `349 484954205842522032303739 md5:001daa50` carried the weight record `HIT XBR 2079` under R3 framing (superseded).
> [R3] Under R3, object `XBR` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `349 4f424a20594a55204b584b md5:489e4ae1` carried the object record `OBJ YJU KXK` under R3 framing (superseded).
> [R3] frame `350 48495420594a552032313136 md5:001e4887` carried the weight record `HIT YJU 2116` under R3 framing (superseded).
> [R3] Under R3, object `YJU` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `350 4f424a205a5258204c344e md5:e6d5c492` carried the object record `OBJ ZRX L4N` under R3 framing (superseded).
> [R3] frame `351 484954205a52582032313533 md5:001ee6be` carried the weight record `HIT ZRX 2153` under R3 framing (superseded).
> [R3] Under R3, object `ZRX` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `351 4f424a20415930204d42522c445031 md5:850d3e43` carried the object record `OBJ AY0 MBR,DP1` under R3 framing (superseded).
> [R3] frame `352 484954204159302032313930 md5:001f84f5` carried the weight record `HIT AY0 2190` under R3 framing (superseded).
> [R3] Under R3, object `AY0` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `352 4f424a20423533202d md5:2344b7f4` carried the object record `OBJ B53 -` under R3 framing (superseded).
> [R3] frame `353 484954204235332032323237 md5:0020232c` carried the weight record `HIT B53 2227` under R3 framing (superseded).
> [R3] Under R3, object `B53` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `353 4f424a2043433620505258 md5:c17c31a5` carried the object record `OBJ CC6 PRX` under R3 framing (superseded).
> [R3] frame `354 484954204343362032323634 md5:0020c163` carried the weight record `HIT CC6 2264` under R3 framing (superseded).
> [R3] Under R3, object `CC6` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `354 4f424a20444b39205159302c474141 md5:5fb3ab56` carried the object record `OBJ DK9 QY0,GAA` under R3 framing (superseded).
> [R3] frame `355 48495420444b392032333031 md5:00215f9a` carried the weight record `HIT DK9 2301` under R3 framing (superseded).
> [R3] Under R3, object `DK9` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `355 4f424a2045534320523533 md5:fdeb2507` carried the object record `OBJ ESC R53` under R3 framing (superseded).
> [R3] frame `356 484954204553432032333338 md5:0021fdd1` carried the weight record `HIT ESC 2338` under R3 framing (superseded).
> [R3] Under R3, object `ESC` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `356 4f424a20465a46202d md5:9c229eb8` carried the object record `OBJ FZF -` under R3 framing (superseded).
> [R3] frame `357 48495420465a462032333735 md5:00229c08` carried the weight record `HIT FZF 2375` under R3 framing (superseded).
> [R3] Under R3, object `FZF` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `357 4f424a2047364a20544b392c4b584b md5:3a5a1869` carried the object record `OBJ G6J TK9,KXK` under R3 framing (superseded).
> [R3] frame `358 4849542047364a2032343132 md5:00233a3f` carried the weight record `HIT G6J 2412` under R3 framing (superseded).
> [R3] Under R3, object `G6J` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `358 4f424a2048444d20555343 md5:d891921a` carried the object record `OBJ HDM USC` under R3 framing (superseded).
> [R3] frame `359 4849542048444d2032343439 md5:0023d876` carried the weight record `HIT HDM 2449` under R3 framing (superseded).
> [R3] Under R3, object `HDM` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `359 4f424a204a4c5120565a46 md5:76c90bcb` carried the object record `OBJ JLQ VZF` under R3 framing (superseded).
> [R3] frame `360 484954204a4c512032343836 md5:002476ad` carried the weight record `HIT JLQ 2486` under R3 framing (superseded).
> [R3] Under R3, object `JLQ` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `360 4f424a204b5454202d md5:1500857c` carried the object record `OBJ KTT -` under R3 framing (superseded).
> [R3] frame `361 484954204b54542032353233 md5:002514e4` carried the weight record `HIT KTT 2523` under R3 framing (superseded).
> [R3] Under R3, object `KTT` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `361 4f424a204c30572058444d md5:b337ff2d` carried the object record `OBJ L0W XDM` under R3 framing (superseded).
> [R3] frame `362 484954204c30572032353630 md5:0025b31b` carried the weight record `HIT L0W 2560` under R3 framing (superseded).
> [R3] Under R3, object `L0W` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `362 4f424a204d375a20594c51 md5:516f78de` carried the object record `OBJ M7Z YLQ` under R3 framing (superseded).
> [R3] frame `363 484954204d375a2032353937 md5:00265152` carried the weight record `HIT M7Z 2597` under R3 framing (superseded).
> [R3] Under R3, object `M7Z` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `363 4f424a204e4532205a54542c523533 md5:efa6f28f` carried the object record `OBJ NE2 ZTT,R53` under R3 framing (superseded).
> [R3] frame `364 484954204e45322032363334 md5:0026ef89` carried the weight record `HIT NE2 2634` under R3 framing (superseded).
> [R3] Under R3, object `NE2` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `364 4f424a20504d35202d md5:8dde6c40` carried the object record `OBJ PM5 -` under R3 framing (superseded).
> [R3] frame `365 48495420504d352032363731 md5:00278dc0` carried the weight record `HIT PM5 2671` under R3 framing (superseded).
> [R3] Under R3, object `PM5` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `365 4f424a205155382042375a md5:2c15e5f1` carried the object record `OBJ QU8 B7Z` under R3 framing (superseded).
> [R3] frame `366 484954205155382032373038 md5:00282bf7` carried the weight record `HIT QU8 2708` under R3 framing (superseded).
> [R3] Under R3, object `QU8` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `366 4f424a20523142204345322c555343 md5:ca4d5fa2` carried the object record `OBJ R1B CE2,USC` under R3 framing (superseded).
> [R3] frame `367 484954205231422032373435 md5:0028ca2e` carried the weight record `HIT R1B 2745` under R3 framing (superseded).
> [R3] Under R3, object `R1B` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `367 4f424a2053384520444d35 md5:6884d953` carried the object record `OBJ S8E DM5` under R3 framing (superseded).
> [R3] frame `368 484954205338452032373832 md5:00296865` carried the weight record `HIT S8E 2782` under R3 framing (superseded).
> [R3] Under R3, object `S8E` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `368 4f424a20544648202d md5:06bc5304` carried the object record `OBJ TFH -` under R3 framing (superseded).
> [R3] frame `369 484954205446482032383139 md5:002a069c` carried the weight record `HIT TFH 2819` under R3 framing (superseded).
> [R3] Under R3, object `TFH` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `369 4f424a20554e4c204631422c58444d md5:a4f3ccb5` carried the object record `OBJ UNL F1B,XDM` under R3 framing (superseded).
> [R3] frame `370 48495420554e4c2032383536 md5:002aa4d3` carried the weight record `HIT UNL 2856` under R3 framing (superseded).
> [R3] Under R3, object `UNL` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `370 4f424a2056565020473845 md5:432b4666` carried the object record `OBJ VVP G8E` under R3 framing (superseded).
> [R3] frame `371 484954205656502032383933 md5:002b430a` carried the weight record `HIT VVP 2893` under R3 framing (superseded).
> [R3] Under R3, object `VVP` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R3] frame `371 4f424a2057325320484648 md5:e162c017` carried the object record `OBJ W2S HFH` under R3 framing (superseded).
> [R3] frame `372 484954205732532032393330 md5:002be141` carried the weight record `HIT W2S 2930` under R3 framing (superseded).
> [R3] Under R3, object `W2S` was reconciled by the inner join on key and ordered with a tie-break by descending weight, and the digest folded it with the weight-sum accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.

### R4 decommissioned examples

The following R4 frames use the five-field with `r4` marker, base64 payload, cksum-of-transport plus byte count envelope. Every one is superseded; they are shown so that the historical shape is on record and so that a reader who greps for record keywords sees the superseded era in bulk. Do not port any of these to R5.

> [R4] frame `400 T0JKIEVVOCAt 1011087813 12 r4` carried the object record `OBJ EU8 -` under R4 framing (superseded).
> [R4] frame `401 SElUIEVVOCA0MDQ= 2350423364 16 r4` carried the weight record `HIT EU8 404` under R4 framing (superseded).
> [R4] Under R4, object `EU8` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `401 T0JKIEYxQiBDSlU= 1233567045 16 r4` carried the object record `OBJ F1B CJU` under R4 framing (superseded).
> [R4] frame `402 SElUIEYxQiA0NDE= 3013353864 16 r4` carried the weight record `HIT F1B 441` under R4 framing (superseded).
> [R4] Under R4, object `F1B` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `402 T0JKIEc4RSBEUlg= 561105439 16 r4` carried the object record `OBJ G8E DRX` under R4 framing (superseded).
> [R4] frame `403 SElUIEc4RSA0Nzg= 1272924359 16 r4` carried the weight record `HIT G8E 478` under R4 framing (superseded).
> [R4] Under R4, object `G8E` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `403 T0JKIEhGSCBFWTAsU0dZ 1861282842 20 r4` carried the object record `OBJ HFH EY0,SGY` under R4 framing (superseded).
> [R4] frame `404 SElUIEhGSCA1MTU= 3079786410 16 r4` carried the weight record `HIT HFH 515` under R4 framing (superseded).
> [R4] Under R4, object `HFH` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `404 T0JKIEpOTCAt 1045457705 12 r4` carried the object record `OBJ JNL -` under R4 framing (superseded).
> [R4] frame `405 SElUIEpOTCA1NTI= 3373255929 16 r4` carried the weight record `HIT JNL 552` under R4 framing (superseded).
> [R4] Under R4, object `JNL` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `405 T0JKIEtWUCBHQzY= 3998918017 16 r4` carried the object record `OBJ KVP GC6` under R4 framing (superseded).
> [R4] frame `406 SElUIEtWUCA1ODk= 1858093586 16 r4` carried the weight record `HIT KVP 589` under R4 framing (superseded).
> [R4] Under R4, object `KVP` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `406 T0JKIEwyUyBISzksVjM3 537274283 20 r4` carried the object record `OBJ L2S HK9,V37` under R4 framing (superseded).
> [R4] frame `407 SElUIEwyUyA2MjY= 4288110595 16 r4` carried the weight record `HIT L2S 626` under R4 framing (superseded).
> [R4] Under R4, object `L2S` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `407 T0JKIE05ViBKU0M= 3424687172 16 r4` carried the object record `OBJ M9V JSC` under R4 framing (superseded).
> [R4] frame `408 SElUIE05ViA2NjM= 1197608166 16 r4` carried the weight record `HIT M9V 663` under R4 framing (superseded).
> [R4] Under R4, object `M9V` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `408 T0JKIE5HWSAt 2982731902 12 r4` carried the object record `OBJ NGY -` under R4 framing (superseded).
> [R4] frame `409 SElUIE5HWSA3MDA= 2112994474 16 r4` carried the weight record `HIT NGY 700` under R4 framing (superseded).
> [R4] Under R4, object `NGY` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `409 T0JKIFBQMSBMNkosWVFH 803878919 20 r4` carried the object record `OBJ PP1 L6J,YQG` under R4 framing (superseded).
> [R4] frame `410 SElUIFBQMSA3Mzc= 577989308 16 r4` carried the weight record `HIT PP1 737` under R4 framing (superseded).
> [R4] Under R4, object `PP1` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `410 T0JKIFFXNCBNRE0= 3560435814 16 r4` carried the object record `OBJ QW4 MDM` under R4 framing (superseded).
> [R4] frame `411 SElUIFFXNCA3NzQ= 531786625 16 r4` carried the weight record `HIT QW4 774` under R4 framing (superseded).
> [R4] Under R4, object `QW4` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `411 T0JKIFIzNyBOTFE= 3085745178 16 r4` carried the object record `OBJ R37 NLQ` under R4 framing (superseded).
> [R4] frame `412 SElUIFIzNyA4MTE= 2954754317 16 r4` carried the weight record `HIT R37 811` under R4 framing (superseded).
> [R4] Under R4, object `R37` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `412 T0JKIFNBQSAt 415926102 12 r4` carried the object record `OBJ SAA -` under R4 framing (superseded).
> [R4] frame `413 SElUIFNBQSA4NDg= 1522537136 16 r4` carried the weight record `HIT SAA 848` under R4 framing (superseded).
> [R4] Under R4, object `SAA` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `413 T0JKIFRIRCBRMFc= 1381223938 16 r4` carried the object record `OBJ THD Q0W` under R4 framing (superseded).
> [R4] frame `414 SElUIFRIRCA4ODU= 2170498502 16 r4` carried the weight record `HIT THD 885` under R4 framing (superseded).
> [R4] Under R4, object `THD` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `414 T0JKIFVRRyBSN1o= 2361553846 16 r4` carried the object record `OBJ UQG R7Z` under R4 framing (superseded).
> [R4] frame `415 SElUIFVRRyA5MjI= 147423428 16 r4` carried the weight record `HIT UQG 922` under R4 framing (superseded).
> [R4] Under R4, object `UQG` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `415 T0JKIFZYSyBTRTIsRVkw 2689234962 20 r4` carried the object record `OBJ VXK SE2,EY0` under R4 framing (superseded).
> [R4] frame `416 SElUIFZYSyA5NTk= 2543911601 16 r4` carried the weight record `HIT VXK 959` under R4 framing (superseded).
> [R4] Under R4, object `VXK` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `416 T0JKIFc0TiAt 3695095390 12 r4` carried the object record `OBJ W4N -` under R4 framing (superseded).
> [R4] frame `417 SElUIFc0TiA5OTY= 1023587021 16 r4` carried the weight record `HIT W4N 996` under R4 framing (superseded).
> [R4] Under R4, object `W4N` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `417 T0JKIFhCUiBVVTg= 1428077085 16 r4` carried the object record `OBJ XBR UU8` under R4 framing (superseded).
> [R4] frame `418 SElUIFhCUiAxMDMz 759907892 16 r4` carried the weight record `HIT XBR 1033` under R4 framing (superseded).
> [R4] Under R4, object `XBR` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `418 T0JKIFlKVSBWMUIsSEs5 2581121443 20 r4` carried the object record `OBJ YJU V1B,HK9` under R4 framing (superseded).
> [R4] frame `419 SElUIFlKVSAxMDcw 2129314817 16 r4` carried the weight record `HIT YJU 1070` under R4 framing (superseded).
> [R4] Under R4, object `YJU` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `419 T0JKIFpSWCBXOEU= 3507887824 16 r4` carried the object record `OBJ ZRX W8E` under R4 framing (superseded).
> [R4] frame `420 SElUIFpSWCAxMTA3 1211525985 16 r4` carried the weight record `HIT ZRX 1107` under R4 framing (superseded).
> [R4] Under R4, object `ZRX` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `420 T0JKIEFZMCAt 4257980211 12 r4` carried the object record `OBJ AY0 -` under R4 framing (superseded).
> [R4] frame `421 SElUIEFZMCAxMTQ0 834285186 16 r4` carried the weight record `HIT AY0 1144` under R4 framing (superseded).
> [R4] Under R4, object `AY0` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `421 T0JKIEI1MyBZTkwsTDZK 3652182366 20 r4` carried the object record `OBJ B53 YNL,L6J` under R4 framing (superseded).
> [R4] frame `422 SElUIEI1MyAxMTgx 260444293 16 r4` carried the weight record `HIT B53 1181` under R4 framing (superseded).
> [R4] Under R4, object `B53` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `422 T0JKIENDNiBaVlA= 1323268645 16 r4` carried the object record `OBJ CC6 ZVP` under R4 framing (superseded).
> [R4] frame `423 SElUIENDNiAxMjE4 2171675015 16 r4` carried the weight record `HIT CC6 1218` under R4 framing (superseded).
> [R4] Under R4, object `CC6` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `423 T0JKIERLOSBBMlM= 4124919878 16 r4` carried the object record `OBJ DK9 A2S` under R4 framing (superseded).
> [R4] frame `424 SElUIERLOSAxMjU1 3849703945 16 r4` carried the weight record `HIT DK9 1255` under R4 framing (superseded).
> [R4] Under R4, object `DK9` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `424 T0JKIEVTQyAt 583761191 12 r4` carried the object record `OBJ ESC -` under R4 framing (superseded).
> [R4] frame `425 SElUIEVTQyAxMjky 1589208505 16 r4` carried the weight record `HIT ESC 1292` under R4 framing (superseded).
> [R4] Under R4, object `ESC` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `425 T0JKIEZaRiBDR1k= 4153456367 16 r4` carried the object record `OBJ FZF CGY` under R4 framing (superseded).
> [R4] frame `426 SElUIEZaRiAxMzI5 1656666956 16 r4` carried the weight record `HIT FZF 1329` under R4 framing (superseded).
> [R4] Under R4, object `FZF` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `426 T0JKIEc2SiBEUDE= 1737556391 16 r4` carried the object record `OBJ G6J DP1` under R4 framing (superseded).
> [R4] frame `427 SElUIEc2SiAxMzY2 1698999837 16 r4` carried the weight record `HIT G6J 1366` under R4 framing (superseded).
> [R4] Under R4, object `G6J` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `427 T0JKIEhETSBFVzQsU0Uy 990527697 20 r4` carried the object record `OBJ HDM EW4,SE2` under R4 framing (superseded).
> [R4] frame `428 SElUIEhETSAxNDAz 2594685216 16 r4` carried the weight record `HIT HDM 1403` under R4 framing (superseded).
> [R4] Under R4, object `HDM` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `428 T0JKIEpMUSAt 3055107063 12 r4` carried the object record `OBJ JLQ -` under R4 framing (superseded).
> [R4] frame `429 SElUIEpMUSAxNDQw 243128797 16 r4` carried the weight record `HIT JLQ 1440` under R4 framing (superseded).
> [R4] Under R4, object `JLQ` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `429 T0JKIEtUVCBHQUE= 3805685025 16 r4` carried the object record `OBJ KTT GAA` under R4 framing (superseded).
> [R4] frame `430 SElUIEtUVCAxNDc3 1130067517 16 r4` carried the weight record `HIT KTT 1477` under R4 framing (superseded).
> [R4] Under R4, object `KTT` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `430 T0JKIEwwVyBISEQsVjFC 2713709502 20 r4` carried the object record `OBJ L0W HHD,V1B` under R4 framing (superseded).
> [R4] frame `431 SElUIEwwVyAxNTE0 1037365651 16 r4` carried the weight record `HIT L0W 1514` under R4 framing (superseded).
> [R4] Under R4, object `L0W` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `431 T0JKIE03WiBKUUc= 2590099061 16 r4` carried the object record `OBJ M7Z JQG` under R4 framing (superseded).
> [R4] frame `432 SElUIE03WiAxNTUx 1696306300 16 r4` carried the weight record `HIT M7Z 1551` under R4 framing (superseded).
> [R4] Under R4, object `M7Z` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `432 T0JKIE5FMiAt 978630975 12 r4` carried the object record `OBJ NE2 -` under R4 framing (superseded).
> [R4] frame `433 SElUIE5FMiAxNTg4 3973709220 16 r4` carried the weight record `HIT NE2 1588` under R4 framing (superseded).
> [R4] Under R4, object `NE2` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `433 T0JKIFBNNSBMNE4sWU5M 3100718787 20 r4` carried the object record `OBJ PM5 L4N,YNL` under R4 framing (superseded).
> [R4] frame `434 SElUIFBNNSAxNjI1 1999861122 16 r4` carried the weight record `HIT PM5 1625` under R4 framing (superseded).
> [R4] Under R4, object `PM5` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `434 T0JKIFFVOCBNQlI= 1950782811 16 r4` carried the object record `OBJ QU8 MBR` under R4 framing (superseded).
> [R4] frame `435 SElUIFFVOCAxNjYy 756889612 16 r4` carried the weight record `HIT QU8 1662` under R4 framing (superseded).
> [R4] Under R4, object `QU8` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `435 T0JKIFIxQiBOSlU= 388114266 16 r4` carried the object record `OBJ R1B NJU` under R4 framing (superseded).
> [R4] frame `436 SElUIFIxQiAxNjk5 2019711250 16 r4` carried the weight record `HIT R1B 1699` under R4 framing (superseded).
> [R4] Under R4, object `R1B` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `436 T0JKIFM4RSAt 1179838654 12 r4` carried the object record `OBJ S8E -` under R4 framing (superseded).
> [R4] frame `437 SElUIFM4RSAxNzM2 1331911219 16 r4` carried the weight record `HIT S8E 1736` under R4 framing (superseded).
> [R4] Under R4, object `S8E` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `437 T0JKIFRGSCBRWTA= 2591685775 16 r4` carried the object record `OBJ TFH QY0` under R4 framing (superseded).
> [R4] frame `438 SElUIFRGSCAxNzcz 917178848 16 r4` carried the weight record `HIT TFH 1773` under R4 framing (superseded).
> [R4] Under R4, object `TFH` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `438 T0JKIFVOTCBSNTM= 674326925 16 r4` carried the object record `OBJ UNL R53` under R4 framing (superseded).
> [R4] frame `439 SElUIFVOTCAxODEw 1377567205 16 r4` carried the weight record `HIT UNL 1810` under R4 framing (superseded).
> [R4] Under R4, object `UNL` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `439 T0JKIFZWUCBTQzYsRVc0 322172258 20 r4` carried the object record `OBJ VVP SC6,EW4` under R4 framing (superseded).
> [R4] frame `440 SElUIFZWUCAxODQ3 3200734258 16 r4` carried the weight record `HIT VVP 1847` under R4 framing (superseded).
> [R4] Under R4, object `VVP` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `440 T0JKIFcyUyAt 1892323706 12 r4` carried the object record `OBJ W2S -` under R4 framing (superseded).
> [R4] frame `441 SElUIFcyUyAxODg0 4049984535 16 r4` carried the weight record `HIT W2S 1884` under R4 framing (superseded).
> [R4] Under R4, object `W2S` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `441 T0JKIFg5ViBVU0M= 409825666 16 r4` carried the object record `OBJ X9V USC` under R4 framing (superseded).
> [R4] frame `442 SElUIFg5ViAxOTIx 148888801 16 r4` carried the weight record `HIT X9V 1921` under R4 framing (superseded).
> [R4] Under R4, object `X9V` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `442 T0JKIFlHWSBWWkYsSEhE 2992770525 20 r4` carried the object record `OBJ YGY VZF,HHD` under R4 framing (superseded).
> [R4] frame `443 SElUIFlHWSAxOTU4 2104881629 16 r4` carried the weight record `HIT YGY 1958` under R4 framing (superseded).
> [R4] Under R4, object `YGY` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `443 T0JKIFpQMSBXNko= 3202551293 16 r4` carried the object record `OBJ ZP1 W6J` under R4 framing (superseded).
> [R4] frame `444 SElUIFpQMSAxOTk1 2453683331 16 r4` carried the weight record `HIT ZP1 1995` under R4 framing (superseded).
> [R4] Under R4, object `ZP1` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `444 T0JKIEFXNCAt 277622100 12 r4` carried the object record `OBJ AW4 -` under R4 framing (superseded).
> [R4] frame `445 SElUIEFXNCAyMDMy 3348906155 16 r4` carried the weight record `HIT AW4 2032` under R4 framing (superseded).
> [R4] Under R4, object `AW4` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `445 T0JKIEIzNyBZTFEsTDRO 4001874782 20 r4` carried the object record `OBJ B37 YLQ,L4N` under R4 framing (superseded).
> [R4] frame `446 SElUIEIzNyAyMDY5 2939874376 16 r4` carried the weight record `HIT B37 2069` under R4 framing (superseded).
> [R4] Under R4, object `B37` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `446 T0JKIENBQSBaVFQ= 579683848 16 r4` carried the object record `OBJ CAA ZTT` under R4 framing (superseded).
> [R4] frame `447 SElUIENBQSAyMTA2 2194977982 16 r4` carried the weight record `HIT CAA 2106` under R4 framing (superseded).
> [R4] Under R4, object `CAA` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `447 T0JKIERIRCBBMFc= 3960021311 16 r4` carried the object record `OBJ DHD A0W` under R4 framing (superseded).
> [R4] frame `448 SElUIERIRCAyMTQz 3823897269 16 r4` carried the weight record `HIT DHD 2143` under R4 framing (superseded).
> [R4] Under R4, object `DHD` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `448 T0JKIEVRRyAt 2737633952 12 r4` carried the object record `OBJ EQG -` under R4 framing (superseded).
> [R4] frame `449 SElUIEVRRyAyMTgw 464572675 16 r4` carried the weight record `HIT EQG 2180` under R4 framing (superseded).
> [R4] Under R4, object `EQG` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `449 T0JKIEZYSyBDRTI= 1829255942 16 r4` carried the object record `OBJ FXK CE2` under R4 framing (superseded).
> [R4] frame `450 SElUIEZYSyAyMjE3 1538110980 16 r4` carried the weight record `HIT FXK 2217` under R4 framing (superseded).
> [R4] Under R4, object `FXK` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `450 T0JKIEc0TiBETTU= 375632604 16 r4` carried the object record `OBJ G4N DM5` under R4 framing (superseded).
> [R4] frame `451 SElUIEc0TiAyMjU0 4065130440 16 r4` carried the weight record `HIT G4N 2254` under R4 framing (superseded).
> [R4] Under R4, object `G4N` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `451 T0JKIEhCUiBFVTgsU0M2 2206257114 20 r4` carried the object record `OBJ HBR EU8,SC6` under R4 framing (superseded).
> [R4] frame `452 SElUIEhCUiAyMjkx 1923101084 16 r4` carried the weight record `HIT HBR 2291` under R4 framing (superseded).
> [R4] Under R4, object `HBR` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `452 T0JKIEpKVSAt 939441264 12 r4` carried the object record `OBJ JJU -` under R4 framing (superseded).
> [R4] frame `453 SElUIEpKVSAyMzI4 3602411767 16 r4` carried the weight record `HIT JJU 2328` under R4 framing (superseded).
> [R4] Under R4, object `JJU` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `453 T0JKIEtSWCBHOEU= 2227030156 16 r4` carried the object record `OBJ KRX G8E` under R4 framing (superseded).
> [R4] frame `454 SElUIEtSWCAyMzY1 3500536338 16 r4` carried the weight record `HIT KRX 2365` under R4 framing (superseded).
> [R4] Under R4, object `KRX` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `454 T0JKIExZMCBIRkgsVlpG 280921540 20 r4` carried the object record `OBJ LY0 HFH,VZF` under R4 framing (superseded).
> [R4] frame `455 SElUIExZMCAyNDAy 772774995 16 r4` carried the weight record `HIT LY0 2402` under R4 framing (superseded).
> [R4] Under R4, object `LY0` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `455 T0JKIE01MyBKTkw= 864282417 16 r4` carried the object record `OBJ M53 JNL` under R4 framing (superseded).
> [R4] frame `456 SElUIE01MyAyNDM5 413432997 16 r4` carried the weight record `HIT M53 2439` under R4 framing (superseded).
> [R4] Under R4, object `M53` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `456 T0JKIE5DNiAt 3608349528 12 r4` carried the object record `OBJ NC6 -` under R4 framing (superseded).
> [R4] frame `457 SElUIE5DNiAyNDc2 4117851809 16 r4` carried the weight record `HIT NC6 2476` under R4 framing (superseded).
> [R4] Under R4, object `NC6` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `457 T0JKIFBLOSBMMlMsWUxR 1211457321 20 r4` carried the object record `OBJ PK9 L2S,YLQ` under R4 framing (superseded).
> [R4] frame `458 SElUIFBLOSAyNTEz 255966856 16 r4` carried the weight record `HIT PK9 2513` under R4 framing (superseded).
> [R4] Under R4, object `PK9` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `458 T0JKIFFTQyBNOVY= 1712706002 16 r4` carried the object record `OBJ QSC M9V` under R4 framing (superseded).
> [R4] frame `459 SElUIFFTQyAyNTUw 1408604875 16 r4` carried the weight record `HIT QSC 2550` under R4 framing (superseded).
> [R4] Under R4, object `QSC` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `459 T0JKIFJaRiBOR1k= 2838768880 16 r4` carried the object record `OBJ RZF NGY` under R4 framing (superseded).
> [R4] frame `460 SElUIFJaRiAyNTg3 254075583 16 r4` carried the weight record `HIT RZF 2587` under R4 framing (superseded).
> [R4] Under R4, object `RZF` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `460 T0JKIFM2SiAt 228752290 12 r4` carried the object record `OBJ S6J -` under R4 framing (superseded).
> [R4] frame `461 SElUIFM2SiAyNjI0 1770555990 16 r4` carried the weight record `HIT S6J 2624` under R4 framing (superseded).
> [R4] Under R4, object `S6J` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `461 T0JKIFRETSBRVzQ= 1655406523 16 r4` carried the object record `OBJ TDM QW4` under R4 framing (superseded).
> [R4] frame `462 SElUIFRETSAyNjYx 775373948 16 r4` carried the weight record `HIT TDM 2661` under R4 framing (superseded).
> [R4] Under R4, object `TDM` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `462 T0JKIFVMUSBSMzc= 1274098723 16 r4` carried the object record `OBJ ULQ R37` under R4 framing (superseded).
> [R4] frame `463 SElUIFVMUSAyNjk4 2336468406 16 r4` carried the weight record `HIT ULQ 2698` under R4 framing (superseded).
> [R4] Under R4, object `ULQ` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `463 T0JKIFZUVCBTQUEsRVU4 1729538164 20 r4` carried the object record `OBJ VTT SAA,EU8` under R4 framing (superseded).
> [R4] frame `464 SElUIFZUVCAyNzM1 1810208636 16 r4` carried the weight record `HIT VTT 2735` under R4 framing (superseded).
> [R4] Under R4, object `VTT` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `464 T0JKIFcwVyAt 678264125 12 r4` carried the object record `OBJ W0W -` under R4 framing (superseded).
> [R4] frame `465 SElUIFcwVyAyNzcy 2460749002 16 r4` carried the weight record `HIT W0W 2772` under R4 framing (superseded).
> [R4] Under R4, object `W0W` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `465 T0JKIFg3WiBVUUc= 1311515571 16 r4` carried the object record `OBJ X7Z UQG` under R4 framing (superseded).
> [R4] frame `466 SElUIFg3WiAyODA5 1244994180 16 r4` carried the weight record `HIT X7Z 2809` under R4 framing (superseded).
> [R4] Under R4, object `X7Z` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `466 T0JKIFlFMiBWWEssSEZI 6850118 20 r4` carried the object record `OBJ YE2 VXK,HFH` under R4 framing (superseded).
> [R4] frame `467 SElUIFlFMiAyODQ2 2382138880 16 r4` carried the weight record `HIT YE2 2846` under R4 framing (superseded).
> [R4] Under R4, object `YE2` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `467 T0JKIFpNNSBXNE4= 2935092486 16 r4` carried the object record `OBJ ZM5 W4N` under R4 framing (superseded).
> [R4] frame `468 SElUIFpNNSAyODgz 1791852652 16 r4` carried the weight record `HIT ZM5 2883` under R4 framing (superseded).
> [R4] Under R4, object `ZM5` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `468 T0JKIEFVOCAt 3660647945 12 r4` carried the object record `OBJ AU8 -` under R4 framing (superseded).
> [R4] frame `469 SElUIEFVOCAyOTIw 567268595 16 r4` carried the weight record `HIT AU8 2920` under R4 framing (superseded).
> [R4] Under R4, object `AU8` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `469 T0JKIEIxQiBZSlUsTDJT 2544259455 20 r4` carried the object record `OBJ B1B YJU,L2S` under R4 framing (superseded).
> [R4] frame `470 SElUIEIxQiAyOTU3 3489393013 16 r4` carried the weight record `HIT B1B 2957` under R4 framing (superseded).
> [R4] Under R4, object `B1B` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `470 T0JKIEM4RSBaUlg= 2870454612 16 r4` carried the object record `OBJ C8E ZRX` under R4 framing (superseded).
> [R4] frame `471 SElUIEM4RSAyOTk0 1501907478 16 r4` carried the weight record `HIT C8E 2994` under R4 framing (superseded).
> [R4] Under R4, object `C8E` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.
> [R4] frame `471 T0JKIERGSCBBWTA= 606278578 16 r4` carried the object record `OBJ DFH AY0` under R4 framing (superseded).
> [R4] frame `472 SElUIERGSCAzMDMx 1727957196 16 r4` carried the weight record `HIT DFH 3031` under R4 framing (superseded).
> [R4] Under R4, object `DFH` was reconciled by the inner join on key and ordered with a tie-break by frame sequence number, and the digest folded it with the FNV-1a accumulator. None of this applies to R5, which inner-joins, tie-breaks by C-locale key, and folds with djb2.

## 10. Appendix B: incident chronicle

A curated selection of incident write-ups from the migration. These explain WHY the rules
are what they are; they contain no current per-frame answers, only process history.

### The delimiter-collision incident (R1) [write-up 1]

A batch of object keys began to include a punctuation suffix during an experimental sharding scheme. Because R1 used a pipe field separator and unescaped payloads, frames split into the wrong number of fields and the importer silently dropped them. The post-mortem recommended an encoded payload and a non-textual-collision separator, motivating the move to a single space with an encoded payload in later revisions.

The review thread that followed ran for several weeks and is summarized here without its per-object decisions, which are not relevant to the current format.

Timeline note: the R1 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The base32 length ticket (R2) [write-up 1]

R2's base32 payloads padded to a multiple of eight characters, and a downstream tool truncated the padding, corrupting one frame in ten thousand. The lesson recorded here is that padding is load-bearing and must be preserved and validated, a principle R5 keeps by requiring canonical padding.

The remediation changed the validator and the importer but not the on-disk record grammar, so downstream consumers were unaffected once the transport was corrected.

Timeline note: the R2 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The tab importer regression (R2) [write-up 1]

The tab-delimited envelope broke a spreadsheet importer that treated consecutive tabs as one separator. R5's single-space separator with an encoded payload avoids the whole class.

A regression test was added that replays a captured descriptor file and compares the plan digest against a golden value; that harness is what eventually caught the next two issues.

Timeline note: the R2 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The MD5 rollback (R3) [write-up 1]

R3's MD5 prefix was cryptographically overkill for a non-adversarial integrity check and cost measurable CPU on the warm path. It was replaced by a CRC. The write-up stresses that the CRC chosen must be the POSIX cksum CRC, not a zlib CRC, because the ops tooling reads the first column of `cksum`.

The retro concluded that the root cause was reusing a rule from the previous revision without re-reading the concern chapter, which is precisely the failure mode this chronicle warns against in Chapter 0.

Timeline note: the R3 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The silent-corruption class (R4) [write-up 1]

The most-cited incident. R4 checksummed the base64 TRANSPORT rather than the decoded CONTENT, so a payload that decoded to the wrong bytes but happened to carry a matching transport CRC passed validation. Several warm plans were built on corrupted objects before the pattern was found. R5's fix is to checksum the decoded bytes only, and to store only the CRC value, not the byte count.

Ops signed off once the first-column `cksum` value matched their existing dashboards, which is why the POSIX cksum CRC (not a zlib CRC) is load-bearing.

Timeline note: the R4 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The phantom warm-up (R2) [write-up 1]

R2's outer join invented a zero weight for objects lacking a HIT record, so cold objects with no measured demand were warmed anyway, wasting origin bandwidth. R5's inner join keeps only objects with both an OBJ and a HIT record.

The review thread that followed ran for several weeks and is summarized here without its per-object decisions, which are not relevant to the current format.

Timeline note: the R2 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The heaviest-first ordering bug (R3) [write-up 1]

R3 broke topological ties by descending hit weight, which made the warm order depend on volatile traffic estimates and produced non-reproducible plans across deploys. R5 breaks ties by the C-locale key order, which is stable.

The remediation changed the validator and the importer but not the on-disk record grammar, so downstream consumers were unaffected once the transport was corrected.

Timeline note: the R3 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The sequence-number ordering bug (R4) [write-up 1]

R4 broke ties by frame sequence number, so re-ordering frames in the file (a no-op for the data) changed the plan. R5's key-based tie-break is independent of frame order.

A regression test was added that replays a captured descriptor file and compares the plan digest against a golden value; that harness is what eventually caught the next two issues.

Timeline note: the R4 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The FNV vs djb2 note (R4) [write-up 1]

R4's digest used FNV-1a; a tooling rewrite standardized on djb2 seeded at 5381 for consistency with the deploy-log hashing library. The values are not interchangeable.

The retro concluded that the root cause was reusing a rule from the previous revision without re-reading the concern chapter, which is precisely the failure mode this chronicle warns against in Chapter 0.

Timeline note: the R4 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The delimiter-collision incident (R1) [write-up 2]

A batch of object keys began to include a punctuation suffix during an experimental sharding scheme. Because R1 used a pipe field separator and unescaped payloads, frames split into the wrong number of fields and the importer silently dropped them. The post-mortem recommended an encoded payload and a non-textual-collision separator, motivating the move to a single space with an encoded payload in later revisions.

The remediation changed the validator and the importer but not the on-disk record grammar, so downstream consumers were unaffected once the transport was corrected.

Timeline note: the R1 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The base32 length ticket (R2) [write-up 2]

R2's base32 payloads padded to a multiple of eight characters, and a downstream tool truncated the padding, corrupting one frame in ten thousand. The lesson recorded here is that padding is load-bearing and must be preserved and validated, a principle R5 keeps by requiring canonical padding.

A regression test was added that replays a captured descriptor file and compares the plan digest against a golden value; that harness is what eventually caught the next two issues.

Timeline note: the R2 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The tab importer regression (R2) [write-up 2]

The tab-delimited envelope broke a spreadsheet importer that treated consecutive tabs as one separator. R5's single-space separator with an encoded payload avoids the whole class.

The retro concluded that the root cause was reusing a rule from the previous revision without re-reading the concern chapter, which is precisely the failure mode this chronicle warns against in Chapter 0.

Timeline note: the R2 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The MD5 rollback (R3) [write-up 2]

R3's MD5 prefix was cryptographically overkill for a non-adversarial integrity check and cost measurable CPU on the warm path. It was replaced by a CRC. The write-up stresses that the CRC chosen must be the POSIX cksum CRC, not a zlib CRC, because the ops tooling reads the first column of `cksum`.

Ops signed off once the first-column `cksum` value matched their existing dashboards, which is why the POSIX cksum CRC (not a zlib CRC) is load-bearing.

Timeline note: the R3 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The silent-corruption class (R4) [write-up 2]

The most-cited incident. R4 checksummed the base64 TRANSPORT rather than the decoded CONTENT, so a payload that decoded to the wrong bytes but happened to carry a matching transport CRC passed validation. Several warm plans were built on corrupted objects before the pattern was found. R5's fix is to checksum the decoded bytes only, and to store only the CRC value, not the byte count.

The review thread that followed ran for several weeks and is summarized here without its per-object decisions, which are not relevant to the current format.

Timeline note: the R4 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The phantom warm-up (R2) [write-up 2]

R2's outer join invented a zero weight for objects lacking a HIT record, so cold objects with no measured demand were warmed anyway, wasting origin bandwidth. R5's inner join keeps only objects with both an OBJ and a HIT record.

The remediation changed the validator and the importer but not the on-disk record grammar, so downstream consumers were unaffected once the transport was corrected.

Timeline note: the R2 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The heaviest-first ordering bug (R3) [write-up 2]

R3 broke topological ties by descending hit weight, which made the warm order depend on volatile traffic estimates and produced non-reproducible plans across deploys. R5 breaks ties by the C-locale key order, which is stable.

A regression test was added that replays a captured descriptor file and compares the plan digest against a golden value; that harness is what eventually caught the next two issues.

Timeline note: the R3 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The sequence-number ordering bug (R4) [write-up 2]

R4 broke ties by frame sequence number, so re-ordering frames in the file (a no-op for the data) changed the plan. R5's key-based tie-break is independent of frame order.

The retro concluded that the root cause was reusing a rule from the previous revision without re-reading the concern chapter, which is precisely the failure mode this chronicle warns against in Chapter 0.

Timeline note: the R4 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The FNV vs djb2 note (R4) [write-up 2]

R4's digest used FNV-1a; a tooling rewrite standardized on djb2 seeded at 5381 for consistency with the deploy-log hashing library. The values are not interchangeable.

Ops signed off once the first-column `cksum` value matched their existing dashboards, which is why the POSIX cksum CRC (not a zlib CRC) is load-bearing.

Timeline note: the R4 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The delimiter-collision incident (R1) [write-up 3]

A batch of object keys began to include a punctuation suffix during an experimental sharding scheme. Because R1 used a pipe field separator and unescaped payloads, frames split into the wrong number of fields and the importer silently dropped them. The post-mortem recommended an encoded payload and a non-textual-collision separator, motivating the move to a single space with an encoded payload in later revisions.

A regression test was added that replays a captured descriptor file and compares the plan digest against a golden value; that harness is what eventually caught the next two issues.

Timeline note: the R1 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The base32 length ticket (R2) [write-up 3]

R2's base32 payloads padded to a multiple of eight characters, and a downstream tool truncated the padding, corrupting one frame in ten thousand. The lesson recorded here is that padding is load-bearing and must be preserved and validated, a principle R5 keeps by requiring canonical padding.

The retro concluded that the root cause was reusing a rule from the previous revision without re-reading the concern chapter, which is precisely the failure mode this chronicle warns against in Chapter 0.

Timeline note: the R2 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The tab importer regression (R2) [write-up 3]

The tab-delimited envelope broke a spreadsheet importer that treated consecutive tabs as one separator. R5's single-space separator with an encoded payload avoids the whole class.

Ops signed off once the first-column `cksum` value matched their existing dashboards, which is why the POSIX cksum CRC (not a zlib CRC) is load-bearing.

Timeline note: the R2 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The MD5 rollback (R3) [write-up 3]

R3's MD5 prefix was cryptographically overkill for a non-adversarial integrity check and cost measurable CPU on the warm path. It was replaced by a CRC. The write-up stresses that the CRC chosen must be the POSIX cksum CRC, not a zlib CRC, because the ops tooling reads the first column of `cksum`.

The review thread that followed ran for several weeks and is summarized here without its per-object decisions, which are not relevant to the current format.

Timeline note: the R3 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The silent-corruption class (R4) [write-up 3]

The most-cited incident. R4 checksummed the base64 TRANSPORT rather than the decoded CONTENT, so a payload that decoded to the wrong bytes but happened to carry a matching transport CRC passed validation. Several warm plans were built on corrupted objects before the pattern was found. R5's fix is to checksum the decoded bytes only, and to store only the CRC value, not the byte count.

The remediation changed the validator and the importer but not the on-disk record grammar, so downstream consumers were unaffected once the transport was corrected.

Timeline note: the R4 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The phantom warm-up (R2) [write-up 3]

R2's outer join invented a zero weight for objects lacking a HIT record, so cold objects with no measured demand were warmed anyway, wasting origin bandwidth. R5's inner join keeps only objects with both an OBJ and a HIT record.

A regression test was added that replays a captured descriptor file and compares the plan digest against a golden value; that harness is what eventually caught the next two issues.

Timeline note: the R2 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The heaviest-first ordering bug (R3) [write-up 3]

R3 broke topological ties by descending hit weight, which made the warm order depend on volatile traffic estimates and produced non-reproducible plans across deploys. R5 breaks ties by the C-locale key order, which is stable.

The retro concluded that the root cause was reusing a rule from the previous revision without re-reading the concern chapter, which is precisely the failure mode this chronicle warns against in Chapter 0.

Timeline note: the R3 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The sequence-number ordering bug (R4) [write-up 3]

R4 broke ties by frame sequence number, so re-ordering frames in the file (a no-op for the data) changed the plan. R5's key-based tie-break is independent of frame order.

Ops signed off once the first-column `cksum` value matched their existing dashboards, which is why the POSIX cksum CRC (not a zlib CRC) is load-bearing.

Timeline note: the R4 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The FNV vs djb2 note (R4) [write-up 3]

R4's digest used FNV-1a; a tooling rewrite standardized on djb2 seeded at 5381 for consistency with the deploy-log hashing library. The values are not interchangeable.

The review thread that followed ran for several weeks and is summarized here without its per-object decisions, which are not relevant to the current format.

Timeline note: the R4 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The delimiter-collision incident (R1) [write-up 4]

A batch of object keys began to include a punctuation suffix during an experimental sharding scheme. Because R1 used a pipe field separator and unescaped payloads, frames split into the wrong number of fields and the importer silently dropped them. The post-mortem recommended an encoded payload and a non-textual-collision separator, motivating the move to a single space with an encoded payload in later revisions.

The retro concluded that the root cause was reusing a rule from the previous revision without re-reading the concern chapter, which is precisely the failure mode this chronicle warns against in Chapter 0.

Timeline note: the R1 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The base32 length ticket (R2) [write-up 4]

R2's base32 payloads padded to a multiple of eight characters, and a downstream tool truncated the padding, corrupting one frame in ten thousand. The lesson recorded here is that padding is load-bearing and must be preserved and validated, a principle R5 keeps by requiring canonical padding.

Ops signed off once the first-column `cksum` value matched their existing dashboards, which is why the POSIX cksum CRC (not a zlib CRC) is load-bearing.

Timeline note: the R2 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The tab importer regression (R2) [write-up 4]

The tab-delimited envelope broke a spreadsheet importer that treated consecutive tabs as one separator. R5's single-space separator with an encoded payload avoids the whole class.

The review thread that followed ran for several weeks and is summarized here without its per-object decisions, which are not relevant to the current format.

Timeline note: the R2 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The MD5 rollback (R3) [write-up 4]

R3's MD5 prefix was cryptographically overkill for a non-adversarial integrity check and cost measurable CPU on the warm path. It was replaced by a CRC. The write-up stresses that the CRC chosen must be the POSIX cksum CRC, not a zlib CRC, because the ops tooling reads the first column of `cksum`.

The remediation changed the validator and the importer but not the on-disk record grammar, so downstream consumers were unaffected once the transport was corrected.

Timeline note: the R3 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The silent-corruption class (R4) [write-up 4]

The most-cited incident. R4 checksummed the base64 TRANSPORT rather than the decoded CONTENT, so a payload that decoded to the wrong bytes but happened to carry a matching transport CRC passed validation. Several warm plans were built on corrupted objects before the pattern was found. R5's fix is to checksum the decoded bytes only, and to store only the CRC value, not the byte count.

A regression test was added that replays a captured descriptor file and compares the plan digest against a golden value; that harness is what eventually caught the next two issues.

Timeline note: the R4 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The phantom warm-up (R2) [write-up 4]

R2's outer join invented a zero weight for objects lacking a HIT record, so cold objects with no measured demand were warmed anyway, wasting origin bandwidth. R5's inner join keeps only objects with both an OBJ and a HIT record.

The retro concluded that the root cause was reusing a rule from the previous revision without re-reading the concern chapter, which is precisely the failure mode this chronicle warns against in Chapter 0.

Timeline note: the R2 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The heaviest-first ordering bug (R3) [write-up 4]

R3 broke topological ties by descending hit weight, which made the warm order depend on volatile traffic estimates and produced non-reproducible plans across deploys. R5 breaks ties by the C-locale key order, which is stable.

Ops signed off once the first-column `cksum` value matched their existing dashboards, which is why the POSIX cksum CRC (not a zlib CRC) is load-bearing.

Timeline note: the R3 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The sequence-number ordering bug (R4) [write-up 4]

R4 broke ties by frame sequence number, so re-ordering frames in the file (a no-op for the data) changed the plan. R5's key-based tie-break is independent of frame order.

The review thread that followed ran for several weeks and is summarized here without its per-object decisions, which are not relevant to the current format.

Timeline note: the R4 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The FNV vs djb2 note (R4) [write-up 4]

R4's digest used FNV-1a; a tooling rewrite standardized on djb2 seeded at 5381 for consistency with the deploy-log hashing library. The values are not interchangeable.

The remediation changed the validator and the importer but not the on-disk record grammar, so downstream consumers were unaffected once the transport was corrected.

Timeline note: the R4 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The delimiter-collision incident (R1) [write-up 5]

A batch of object keys began to include a punctuation suffix during an experimental sharding scheme. Because R1 used a pipe field separator and unescaped payloads, frames split into the wrong number of fields and the importer silently dropped them. The post-mortem recommended an encoded payload and a non-textual-collision separator, motivating the move to a single space with an encoded payload in later revisions.

Ops signed off once the first-column `cksum` value matched their existing dashboards, which is why the POSIX cksum CRC (not a zlib CRC) is load-bearing.

Timeline note: the R1 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The base32 length ticket (R2) [write-up 5]

R2's base32 payloads padded to a multiple of eight characters, and a downstream tool truncated the padding, corrupting one frame in ten thousand. The lesson recorded here is that padding is load-bearing and must be preserved and validated, a principle R5 keeps by requiring canonical padding.

The review thread that followed ran for several weeks and is summarized here without its per-object decisions, which are not relevant to the current format.

Timeline note: the R2 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The tab importer regression (R2) [write-up 5]

The tab-delimited envelope broke a spreadsheet importer that treated consecutive tabs as one separator. R5's single-space separator with an encoded payload avoids the whole class.

The remediation changed the validator and the importer but not the on-disk record grammar, so downstream consumers were unaffected once the transport was corrected.

Timeline note: the R2 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The MD5 rollback (R3) [write-up 5]

R3's MD5 prefix was cryptographically overkill for a non-adversarial integrity check and cost measurable CPU on the warm path. It was replaced by a CRC. The write-up stresses that the CRC chosen must be the POSIX cksum CRC, not a zlib CRC, because the ops tooling reads the first column of `cksum`.

A regression test was added that replays a captured descriptor file and compares the plan digest against a golden value; that harness is what eventually caught the next two issues.

Timeline note: the R3 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The silent-corruption class (R4) [write-up 5]

The most-cited incident. R4 checksummed the base64 TRANSPORT rather than the decoded CONTENT, so a payload that decoded to the wrong bytes but happened to carry a matching transport CRC passed validation. Several warm plans were built on corrupted objects before the pattern was found. R5's fix is to checksum the decoded bytes only, and to store only the CRC value, not the byte count.

The retro concluded that the root cause was reusing a rule from the previous revision without re-reading the concern chapter, which is precisely the failure mode this chronicle warns against in Chapter 0.

Timeline note: the R4 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The phantom warm-up (R2) [write-up 5]

R2's outer join invented a zero weight for objects lacking a HIT record, so cold objects with no measured demand were warmed anyway, wasting origin bandwidth. R5's inner join keeps only objects with both an OBJ and a HIT record.

Ops signed off once the first-column `cksum` value matched their existing dashboards, which is why the POSIX cksum CRC (not a zlib CRC) is load-bearing.

Timeline note: the R2 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The heaviest-first ordering bug (R3) [write-up 5]

R3 broke topological ties by descending hit weight, which made the warm order depend on volatile traffic estimates and produced non-reproducible plans across deploys. R5 breaks ties by the C-locale key order, which is stable.

The review thread that followed ran for several weeks and is summarized here without its per-object decisions, which are not relevant to the current format.

Timeline note: the R3 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The sequence-number ordering bug (R4) [write-up 5]

R4 broke ties by frame sequence number, so re-ordering frames in the file (a no-op for the data) changed the plan. R5's key-based tie-break is independent of frame order.

The remediation changed the validator and the importer but not the on-disk record grammar, so downstream consumers were unaffected once the transport was corrected.

Timeline note: the R4 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The FNV vs djb2 note (R4) [write-up 5]

R4's digest used FNV-1a; a tooling rewrite standardized on djb2 seeded at 5381 for consistency with the deploy-log hashing library. The values are not interchangeable.

A regression test was added that replays a captured descriptor file and compares the plan digest against a golden value; that harness is what eventually caught the next two issues.

Timeline note: the R4 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The delimiter-collision incident (R1) [write-up 6]

A batch of object keys began to include a punctuation suffix during an experimental sharding scheme. Because R1 used a pipe field separator and unescaped payloads, frames split into the wrong number of fields and the importer silently dropped them. The post-mortem recommended an encoded payload and a non-textual-collision separator, motivating the move to a single space with an encoded payload in later revisions.

The review thread that followed ran for several weeks and is summarized here without its per-object decisions, which are not relevant to the current format.

Timeline note: the R1 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The base32 length ticket (R2) [write-up 6]

R2's base32 payloads padded to a multiple of eight characters, and a downstream tool truncated the padding, corrupting one frame in ten thousand. The lesson recorded here is that padding is load-bearing and must be preserved and validated, a principle R5 keeps by requiring canonical padding.

The remediation changed the validator and the importer but not the on-disk record grammar, so downstream consumers were unaffected once the transport was corrected.

Timeline note: the R2 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The tab importer regression (R2) [write-up 6]

The tab-delimited envelope broke a spreadsheet importer that treated consecutive tabs as one separator. R5's single-space separator with an encoded payload avoids the whole class.

A regression test was added that replays a captured descriptor file and compares the plan digest against a golden value; that harness is what eventually caught the next two issues.

Timeline note: the R2 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The MD5 rollback (R3) [write-up 6]

R3's MD5 prefix was cryptographically overkill for a non-adversarial integrity check and cost measurable CPU on the warm path. It was replaced by a CRC. The write-up stresses that the CRC chosen must be the POSIX cksum CRC, not a zlib CRC, because the ops tooling reads the first column of `cksum`.

The retro concluded that the root cause was reusing a rule from the previous revision without re-reading the concern chapter, which is precisely the failure mode this chronicle warns against in Chapter 0.

Timeline note: the R3 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The silent-corruption class (R4) [write-up 6]

The most-cited incident. R4 checksummed the base64 TRANSPORT rather than the decoded CONTENT, so a payload that decoded to the wrong bytes but happened to carry a matching transport CRC passed validation. Several warm plans were built on corrupted objects before the pattern was found. R5's fix is to checksum the decoded bytes only, and to store only the CRC value, not the byte count.

Ops signed off once the first-column `cksum` value matched their existing dashboards, which is why the POSIX cksum CRC (not a zlib CRC) is load-bearing.

Timeline note: the R4 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The phantom warm-up (R2) [write-up 6]

R2's outer join invented a zero weight for objects lacking a HIT record, so cold objects with no measured demand were warmed anyway, wasting origin bandwidth. R5's inner join keeps only objects with both an OBJ and a HIT record.

The review thread that followed ran for several weeks and is summarized here without its per-object decisions, which are not relevant to the current format.

Timeline note: the R2 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The heaviest-first ordering bug (R3) [write-up 6]

R3 broke topological ties by descending hit weight, which made the warm order depend on volatile traffic estimates and produced non-reproducible plans across deploys. R5 breaks ties by the C-locale key order, which is stable.

The remediation changed the validator and the importer but not the on-disk record grammar, so downstream consumers were unaffected once the transport was corrected.

Timeline note: the R3 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The sequence-number ordering bug (R4) [write-up 6]

R4 broke ties by frame sequence number, so re-ordering frames in the file (a no-op for the data) changed the plan. R5's key-based tie-break is independent of frame order.

A regression test was added that replays a captured descriptor file and compares the plan digest against a golden value; that harness is what eventually caught the next two issues.

Timeline note: the R4 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

### The FNV vs djb2 note (R4) [write-up 6]

R4's digest used FNV-1a; a tooling rewrite standardized on djb2 seeded at 5381 for consistency with the deploy-log hashing library. The values are not interchangeable.

The retro concluded that the root cause was reusing a rule from the previous revision without re-reading the concern chapter, which is precisely the failure mode this chronicle warns against in Chapter 0.

Timeline note: the R4 behavior described above was retired in the migration to the next revision; by R5 the corresponding concern-chapter rule is the only one that applies. The details are preserved here as process history, not as a current specification, and they intentionally add reading volume between the current rules so that the live contract must be synthesized rather than skimmed.

## 10b. Appendix B2: design-review thread excerpts

Lightly edited excerpts from the format-review threads across the migration. They recordthe reasoning behind each revision's choices. They contain no current per-frame answers.

### Thread: envelope separator (round 1)

> The transport owner opened the discussion on envelope separator, arguing from the previous revision's incident history. The concern was whether to keep a textual separator or move to a length-prefixed frame. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The ops liaison replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: payload encoding (round 1)

> The planner owner opened the discussion on payload encoding, arguing from the previous revision's incident history. The concern was the trade-off between hex readability, base32 case-insensitivity, and base64 density. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The importer maintainer replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: checksum domain (round 1)

> The ops liaison opened the discussion on checksum domain, arguing from the previous revision's incident history. The concern was whether the integrity value should cover the transport bytes or the decoded content. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The on-call lead replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: record kinds (round 1)

> The importer maintainer opened the discussion on record kinds, arguing from the previous revision's incident history. The concern was whether to keep a single record kind or split objects from weights. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The release manager replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: join type (round 1)

> The on-call lead opened the discussion on join type, arguing from the previous revision's incident history. The concern was inner versus outer reconciliation and how to treat weightless objects. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The transport owner replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: ordering tie-break (round 1)

> The release manager opened the discussion on ordering tie-break, arguing from the previous revision's incident history. The concern was weight-based, sequence-based, or key-based tie-breaks and their reproducibility. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The planner owner replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: digest accumulator (round 1)

> The transport owner opened the discussion on digest accumulator, arguing from the previous revision's incident history. The concern was which rolling hash the deploy log should standardize on. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The ops liaison replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: envelope separator (round 2)

> The planner owner opened the discussion on envelope separator, arguing from the previous revision's incident history. The concern was whether to keep a textual separator or move to a length-prefixed frame. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The importer maintainer replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: payload encoding (round 2)

> The ops liaison opened the discussion on payload encoding, arguing from the previous revision's incident history. The concern was the trade-off between hex readability, base32 case-insensitivity, and base64 density. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The on-call lead replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: checksum domain (round 2)

> The importer maintainer opened the discussion on checksum domain, arguing from the previous revision's incident history. The concern was whether the integrity value should cover the transport bytes or the decoded content. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The release manager replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: record kinds (round 2)

> The on-call lead opened the discussion on record kinds, arguing from the previous revision's incident history. The concern was whether to keep a single record kind or split objects from weights. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The transport owner replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: join type (round 2)

> The release manager opened the discussion on join type, arguing from the previous revision's incident history. The concern was inner versus outer reconciliation and how to treat weightless objects. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The planner owner replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: ordering tie-break (round 2)

> The transport owner opened the discussion on ordering tie-break, arguing from the previous revision's incident history. The concern was weight-based, sequence-based, or key-based tie-breaks and their reproducibility. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The ops liaison replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: digest accumulator (round 2)

> The planner owner opened the discussion on digest accumulator, arguing from the previous revision's incident history. The concern was which rolling hash the deploy log should standardize on. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The importer maintainer replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: envelope separator (round 3)

> The ops liaison opened the discussion on envelope separator, arguing from the previous revision's incident history. The concern was whether to keep a textual separator or move to a length-prefixed frame. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The on-call lead replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: payload encoding (round 3)

> The importer maintainer opened the discussion on payload encoding, arguing from the previous revision's incident history. The concern was the trade-off between hex readability, base32 case-insensitivity, and base64 density. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The release manager replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: checksum domain (round 3)

> The on-call lead opened the discussion on checksum domain, arguing from the previous revision's incident history. The concern was whether the integrity value should cover the transport bytes or the decoded content. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The transport owner replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: record kinds (round 3)

> The release manager opened the discussion on record kinds, arguing from the previous revision's incident history. The concern was whether to keep a single record kind or split objects from weights. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The planner owner replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: join type (round 3)

> The transport owner opened the discussion on join type, arguing from the previous revision's incident history. The concern was inner versus outer reconciliation and how to treat weightless objects. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The ops liaison replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: ordering tie-break (round 3)

> The planner owner opened the discussion on ordering tie-break, arguing from the previous revision's incident history. The concern was weight-based, sequence-based, or key-based tie-breaks and their reproducibility. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The importer maintainer replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: digest accumulator (round 3)

> The ops liaison opened the discussion on digest accumulator, arguing from the previous revision's incident history. The concern was which rolling hash the deploy log should standardize on. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The on-call lead replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: envelope separator (round 4)

> The importer maintainer opened the discussion on envelope separator, arguing from the previous revision's incident history. The concern was whether to keep a textual separator or move to a length-prefixed frame. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The release manager replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: payload encoding (round 4)

> The on-call lead opened the discussion on payload encoding, arguing from the previous revision's incident history. The concern was the trade-off between hex readability, base32 case-insensitivity, and base64 density. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The transport owner replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: checksum domain (round 4)

> The release manager opened the discussion on checksum domain, arguing from the previous revision's incident history. The concern was whether the integrity value should cover the transport bytes or the decoded content. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The planner owner replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: record kinds (round 4)

> The transport owner opened the discussion on record kinds, arguing from the previous revision's incident history. The concern was whether to keep a single record kind or split objects from weights. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The ops liaison replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: join type (round 4)

> The planner owner opened the discussion on join type, arguing from the previous revision's incident history. The concern was inner versus outer reconciliation and how to treat weightless objects. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The importer maintainer replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: ordering tie-break (round 4)

> The ops liaison opened the discussion on ordering tie-break, arguing from the previous revision's incident history. The concern was weight-based, sequence-based, or key-based tie-breaks and their reproducibility. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The on-call lead replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: digest accumulator (round 4)

> The importer maintainer opened the discussion on digest accumulator, arguing from the previous revision's incident history. The concern was which rolling hash the deploy log should standardize on. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The release manager replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: envelope separator (round 5)

> The on-call lead opened the discussion on envelope separator, arguing from the previous revision's incident history. The concern was whether to keep a textual separator or move to a length-prefixed frame. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The transport owner replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: payload encoding (round 5)

> The release manager opened the discussion on payload encoding, arguing from the previous revision's incident history. The concern was the trade-off between hex readability, base32 case-insensitivity, and base64 density. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The planner owner replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: checksum domain (round 5)

> The transport owner opened the discussion on checksum domain, arguing from the previous revision's incident history. The concern was whether the integrity value should cover the transport bytes or the decoded content. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The ops liaison replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: record kinds (round 5)

> The planner owner opened the discussion on record kinds, arguing from the previous revision's incident history. The concern was whether to keep a single record kind or split objects from weights. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The importer maintainer replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: join type (round 5)

> The ops liaison opened the discussion on join type, arguing from the previous revision's incident history. The concern was inner versus outer reconciliation and how to treat weightless objects. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The on-call lead replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: ordering tie-break (round 5)

> The importer maintainer opened the discussion on ordering tie-break, arguing from the previous revision's incident history. The concern was weight-based, sequence-based, or key-based tie-breaks and their reproducibility. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The release manager replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: digest accumulator (round 5)

> The on-call lead opened the discussion on digest accumulator, arguing from the previous revision's incident history. The concern was which rolling hash the deploy log should standardize on. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The transport owner replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: envelope separator (round 6)

> The release manager opened the discussion on envelope separator, arguing from the previous revision's incident history. The concern was whether to keep a textual separator or move to a length-prefixed frame. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The planner owner replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: payload encoding (round 6)

> The transport owner opened the discussion on payload encoding, arguing from the previous revision's incident history. The concern was the trade-off between hex readability, base32 case-insensitivity, and base64 density. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The ops liaison replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: checksum domain (round 6)

> The planner owner opened the discussion on checksum domain, arguing from the previous revision's incident history. The concern was whether the integrity value should cover the transport bytes or the decoded content. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The importer maintainer replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: record kinds (round 6)

> The ops liaison opened the discussion on record kinds, arguing from the previous revision's incident history. The concern was whether to keep a single record kind or split objects from weights. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The on-call lead replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: join type (round 6)

> The importer maintainer opened the discussion on join type, arguing from the previous revision's incident history. The concern was inner versus outer reconciliation and how to treat weightless objects. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The release manager replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: ordering tie-break (round 6)

> The on-call lead opened the discussion on ordering tie-break, arguing from the previous revision's incident history. The concern was weight-based, sequence-based, or key-based tie-breaks and their reproducibility. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The transport owner replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: digest accumulator (round 6)

> The release manager opened the discussion on digest accumulator, arguing from the previous revision's incident history. The concern was which rolling hash the deploy log should standardize on. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The planner owner replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: envelope separator (round 7)

> The transport owner opened the discussion on envelope separator, arguing from the previous revision's incident history. The concern was whether to keep a textual separator or move to a length-prefixed frame. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The ops liaison replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: payload encoding (round 7)

> The planner owner opened the discussion on payload encoding, arguing from the previous revision's incident history. The concern was the trade-off between hex readability, base32 case-insensitivity, and base64 density. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The importer maintainer replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: checksum domain (round 7)

> The ops liaison opened the discussion on checksum domain, arguing from the previous revision's incident history. The concern was whether the integrity value should cover the transport bytes or the decoded content. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The on-call lead replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: record kinds (round 7)

> The importer maintainer opened the discussion on record kinds, arguing from the previous revision's incident history. The concern was whether to keep a single record kind or split objects from weights. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The release manager replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: join type (round 7)

> The on-call lead opened the discussion on join type, arguing from the previous revision's incident history. The concern was inner versus outer reconciliation and how to treat weightless objects. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The transport owner replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: ordering tie-break (round 7)

> The release manager opened the discussion on ordering tie-break, arguing from the previous revision's incident history. The concern was weight-based, sequence-based, or key-based tie-breaks and their reproducibility. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The planner owner replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: digest accumulator (round 7)

> The transport owner opened the discussion on digest accumulator, arguing from the previous revision's incident history. The concern was which rolling hash the deploy log should standardize on. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The ops liaison replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: envelope separator (round 8)

> The planner owner opened the discussion on envelope separator, arguing from the previous revision's incident history. The concern was whether to keep a textual separator or move to a length-prefixed frame. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The importer maintainer replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: payload encoding (round 8)

> The ops liaison opened the discussion on payload encoding, arguing from the previous revision's incident history. The concern was the trade-off between hex readability, base32 case-insensitivity, and base64 density. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The on-call lead replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: checksum domain (round 8)

> The importer maintainer opened the discussion on checksum domain, arguing from the previous revision's incident history. The concern was whether the integrity value should cover the transport bytes or the decoded content. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The release manager replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: record kinds (round 8)

> The on-call lead opened the discussion on record kinds, arguing from the previous revision's incident history. The concern was whether to keep a single record kind or split objects from weights. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The transport owner replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: join type (round 8)

> The release manager opened the discussion on join type, arguing from the previous revision's incident history. The concern was inner versus outer reconciliation and how to treat weightless objects. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The planner owner replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: ordering tie-break (round 8)

> The transport owner opened the discussion on ordering tie-break, arguing from the previous revision's incident history. The concern was weight-based, sequence-based, or key-based tie-breaks and their reproducibility. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The ops liaison replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: digest accumulator (round 8)

> The planner owner opened the discussion on digest accumulator, arguing from the previous revision's incident history. The concern was which rolling hash the deploy log should standardize on. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The importer maintainer replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: envelope separator (round 9)

> The ops liaison opened the discussion on envelope separator, arguing from the previous revision's incident history. The concern was whether to keep a textual separator or move to a length-prefixed frame. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The on-call lead replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: payload encoding (round 9)

> The importer maintainer opened the discussion on payload encoding, arguing from the previous revision's incident history. The concern was the trade-off between hex readability, base32 case-insensitivity, and base64 density. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The release manager replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: checksum domain (round 9)

> The on-call lead opened the discussion on checksum domain, arguing from the previous revision's incident history. The concern was whether the integrity value should cover the transport bytes or the decoded content. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The transport owner replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: record kinds (round 9)

> The release manager opened the discussion on record kinds, arguing from the previous revision's incident history. The concern was whether to keep a single record kind or split objects from weights. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The planner owner replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: join type (round 9)

> The transport owner opened the discussion on join type, arguing from the previous revision's incident history. The concern was inner versus outer reconciliation and how to treat weightless objects. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The ops liaison replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: ordering tie-break (round 9)

> The planner owner opened the discussion on ordering tie-break, arguing from the previous revision's incident history. The concern was weight-based, sequence-based, or key-based tie-breaks and their reproducibility. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The importer maintainer replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

### Thread: digest accumulator (round 9)

> The ops liaison opened the discussion on digest accumulator, arguing from the previous revision's incident history. The concern was which rolling hash the deploy log should standardize on. The thread weighed the operational cost against the reproducibility of the resulting plans.

> The on-call lead replied that whatever was chosen had to be validated at ingest, because a silently-accepted malformed frame is worse than a rejected one; the group agreed that ingest validation with explicit error codes was mandatory, which is why R5 enumerates a fixed set of codes rather than dropping bad frames.

> The thread closed by deferring the concrete rule to the concern chapter for the next revision; the decision recorded there superseded this discussion. This excerpt is retained only for the reasoning, not for any rule an implementer should copy.

## 11. Appendix C: R5 quick contract (normative summary)

This is a convenience summary of the CURRENT (R5) rules gathered from the chapters above.
Where this summary and a chapter appear to differ, the chapter text governs.

- Frame: `SEQ PAYLOAD CRC`, three space-separated fields, one per line; blanks skipped.
- SEQ: positive decimal, no leading zeros.
- PAYLOAD: canonical RFC-4648 base64 (standard alphabet, `=` padding, round-trips).
- CRC: decimal POSIX `cksum` CRC of the DECODED bytes, value only.
- Record: `OBJ key prereqs` (`-` or comma list) or `HIT key w` (<=9-digit int); key `[A-Z][A-Z0-9]{1,5}`.
- Codes: BAD_FRAME, BAD_B64, BAD_CRC, BAD_REC, BAD_KIND, BAD_KEY, BAD_PRE, BAD_HITS, DUP.
- Join: inner join OBJ x HIT on key; dangling prereqs reported, not added.
- Order: topological, ties broken by C-locale key ascending; unresolvable on a cycle.
- Digest: djb2 (seed 5381, mul 33) over order key bytes; hit_sum; cksum of `key\n...`.

## 12. Appendix D: full decommissioned specifications (DO NOT IMPLEMENT)

For completeness, the full contracts of R1..R4 are reproduced. They are decommissioned in
their entirety. They are the single largest source of plausible-but-wrong rules in this
document; every line below is superseded by the chapters above.

### R1 full contract (decommissioned)

- [R1] Envelope: `seq|payload|sum`, pipe-separated, payload escaped with backslash.
- [R1] Encoding: raw ASCII payload (no transport encoding).
- [R1] Integrity: `sum` = (sum of payload bytes) mod 65536.
- [R1] Grammar: single-kind `key deps weight` colon-free, space separated.
- [R1] Join: none; every record stood alone.
- [R1] Order: file order.
- [R1] Digest: sum of weights.

### R2 full contract (decommissioned)

- [R2] Envelope: `seq<TAB>payload<TAB>sum`, tab-separated.
- [R2] Encoding: RFC-4648 base32 (`A-Z2-7`, `=` padding).
- [R2] Integrity: additive checksum as R1.
- [R2] Grammar: two kinds `OBJ`/`WGT` (note: `WGT`, not `HIT`), colon after key.
- [R2] Join: OUTER join; missing weights defaulted to 0.
- [R2] Order: topological, ties by ascending key.
- [R2] Digest: sum of weights only.

### R3 full contract (decommissioned)

- [R3] Envelope: `seq payload md5:HEX`, space-separated, trailing length omitted.
- [R3] Encoding: lowercase hex.
- [R3] Integrity: MD5 prefix of the decoded bytes (first 8 hex shown).
- [R3] Grammar: `NODE`/`COST` kinds, colon-separated tokens.
- [R3] Join: inner join on key.
- [R3] Order: topological, ties by DESCENDING weight.
- [R3] Digest: sum of weights.

### R4 full contract (decommissioned)

- [R4] Envelope: `seq payload crc bytecount r4`, five fields incl. trailing `r4` marker.
- [R4] Encoding: canonical base64 (this part R5 kept).
- [R4] Integrity: POSIX cksum CRC of the BASE64 TEXT, stored with the byte count.
- [R4] Grammar: `OBJ`/`HIT` kinds, space separated (this part R5 kept).
- [R4] Join: inner join on key (this part R5 kept).
- [R4] Order: topological, ties by frame SEQUENCE number.
- [R4] Digest: FNV-1a over concatenated keys.

## 13. Appendix E: glossary

- **Frame**: one physical line of `warmcache.dat`.
- **Payload**: the encoded record within a frame.
- **Record**: the decoded OBJ/HIT statement.
- **Object (OBJ)**: a cache object and its prerequisite objects.
- **Hit (HIT)**: an object's integer hit weight.
- **Join**: the inner reconciliation of OBJ and HIT records by key.
- **Dangling prerequisite**: a prerequisite of a joined object that is not itself joined.
- **Warm-up order**: the topological order in which objects are warmed.
- **Plan digest**: the djb2 hash, hit sum, and cksum of the finished order.
- **POSIX cksum CRC**: the CRC-32 that `/usr/bin/cksum` prints in its first column.
- **Canonical base64**: base64 that round-trips through a conformant encoder.
- **C-locale order**: bytewise ASCII comparison (`LC_ALL=C sort`).

