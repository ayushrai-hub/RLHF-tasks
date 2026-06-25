# Index contract

`trace_index.json` uses `schema_tag` `tb3-kdiff-trace-01`.

Schema fields:
- `sources_scanned` means the count of Markdown runbooks scanned under `/app/docs/q3_bundles`.
- `trace_blocks` means the total fenced trace excerpts harvested.
- `fence_kinds` means the distinct fence labels present (`strace`, `lsof`).
- `blocks[].source_path` means the runbook path relative to the bundles root.

| field | type | meaning |
|-------|------|---------|
| sources_scanned | int | Markdown runbooks scanned under `/app/docs/q3_bundles` |
| trace_blocks | int | Total fenced trace excerpts harvested |
| fence_kinds | string[] | Distinct fence labels (`strace`, `lsof`) |
| blocks[].source_path | string | Runbook path relative to the bundles root |
| blocks[].fence_kind | string | Fence label |
| blocks[].line_count | int | Lines inside the fence body |

The index pass must harvest every fenced `strace` and `lsof` block from all seven runbooks without rerunning the Monte Carlo workflow. The current bundle set contains fifteen fenced excerpts total.
