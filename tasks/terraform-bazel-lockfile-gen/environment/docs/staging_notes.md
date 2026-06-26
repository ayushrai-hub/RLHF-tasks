# Staging notes

QA rotation across alpha, beta, gamma, delta, and epsilon still shows:

- Returning to an entry after a latest-series run upgrades pins that should have stayed sealed in that entry's slot
- Replay witnesses record the wrong matrix entry but hydrate still treats the slot as warm
- Journal chain lines disagree on prefix linkage even though generation counters advance
- Module-lock stub rollups hash the wrong material and lines key off module ids instead of repo keys
- Checksum rows diverge from the depot sidecar on port 8787
- Tampered output files survive the next apply when the link digest is unchanged

See `/app/environment/docs/artifact_shapes.md` and `/app/environment/docs/vol_h/` for normative shapes and amendment rules.
