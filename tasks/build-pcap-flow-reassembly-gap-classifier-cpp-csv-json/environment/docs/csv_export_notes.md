# CSV Export Notes

The CSV files are usually exported from packet tools with fields already normalized to stream direction. Sequence numbers are absolute within the captured stream, not relative display numbers.

Blank lines can appear after manual edits and should not be counted as data rows. Malformed data rows remain useful for audit trails, so the analyzer reports deterministic diagnostics instead of aborting the whole run.
