The diffusion Monte Carlo batch is done; the only evidence left is seven Markdown runbooks under `/app/docs/q3_bundles/` with embedded strace and lsof excerpts. A Kotlin Gradle desk at `/app` should scan those docs and reconstruct file and socket usage without rerunning the workflow.

Build with `bash /app/scripts/build_all.sh`, then run the index pass so every fenced `strace` and `lsof` excerpt is harvested with its source runbook recorded. Run `bash /app/scripts/milestone_probes.sh index`. The probe must write `/app/output/trace_index.json` with `schema_tag` `tb3-kdiff-trace-01`, `sources_scanned` `7`, `trace_blocks` `15`, both kinds in `fence_kinds`, and populated `source_path` values per `/app/docs/index_contract.md`. After the probe, open that JSON and confirm those fields; a silent exit alone is not enough, and wrong counts mean the Kotlin harvest code still needs fixing.

Signal completion once the index probe passes.
