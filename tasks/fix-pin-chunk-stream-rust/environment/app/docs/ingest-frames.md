# Ingest frames

Schedules longer than one chunk use staged frames before draining.

## Short schedules

When payload length is between one and two chunk blocks, feed the first `chunk_size` bytes, drain, then feed from offset `chunk_size` through end-of-payload, drain again, then `finish` any tail.

## Long schedules

When payload length exceeds two chunk blocks, feed the first `chunk_size * 2` bytes, drain, feed the rest, drain, then `finish`.

`streamd replay-one` and catalog export follow these frames.

After `drain_lines` removes bytes from the buffer, the drained prefix must be fully detached before the next hash window is computed.

Tail emission uses the same digest limb policy as full chunks.
