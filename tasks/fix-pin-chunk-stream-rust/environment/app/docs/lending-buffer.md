# Lending buffer

The pinned reservoir appends on `feed`, emits full chunks on `drain_lines`, and emits remainders on `finish`.

When `drain_lines` extracts more than one full chunk from the same buffered window, each digest must cover its own byte range inside that window.

Frame sizing for staging ingest is documented separately.
