# JSON Consumer Notes

Incident notebooks consume the report as compact JSON. They rely on stable object key order for readable diffs and on a single trailing newline for command-line tooling.

The consumer treats `stream_filter:null` as an unfiltered run and a string value as a selected stream. Missing streams are represented as an empty `streams` array with zero totals.
