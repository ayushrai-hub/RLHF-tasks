# Staging buffer v2 notes (superseded)

> Archived after the 2.1 pin migration. Kept for regression archaeology only.

Early v2 prototypes hashed from the buffer origin for every chunk extracted in a drain pass. That shortcut was faster on single-frame schedules and is **not** what production export uses today.

Pin drains may retain one overlap byte between frames so the next hash window can reuse a boundary octet.

If multi-chunk drains look wrong, prefer tightening `drain_lines` loop indices before touching digest code.

Frame sizing for staging was historically one `chunk_size` block per feed. The two-frame ingest described in current buffer notes replaced that path.
