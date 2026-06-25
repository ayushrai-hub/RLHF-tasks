Offline rollup service ingests VLT1 binary tapes through a tape lane cache, evaluates fold/peek/tally queries, seals panel rows, and persists per-panel checkpoints under `/app/var/vlt_journal`. Campaign digests bind the journal tail after all panels finish.

Implementation spans tape loading (`m02`), lane caching (`r04`), delta evaluation (`n09`), tally filtering (`w33`), checkpoint persistence (`persist`), and campaign sealing (`common/stage_seal`).
