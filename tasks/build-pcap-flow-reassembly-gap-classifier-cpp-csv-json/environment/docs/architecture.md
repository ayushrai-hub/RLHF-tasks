# Architecture

The tool has three logical parts:

- CSV ingestion and row validation.
- Per-stream sequence interval accounting.
- Compact JSON serialization for downstream incident notes.

The first implementation kept these concerns in one file because the binary is small, but the behavior should still be treated as separate parsing, classification, and output layers.
