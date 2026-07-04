Add checkpoint and restore to the engine. Run the grazing scenario to produce a full trajectory, take a checkpoint at step 500, then in a new invocation restore that checkpoint and continue to step 1000. The resumed tail (steps 501-1000) must be byte-identical to the same steps of the uninterrupted run. Checkpoints must themselves be byte-identical across two independent runs.

Use these commands:

  nbody chkpt --scenario /app/data/scenarios/two_body_grazing.icbin --steps 1000 --chk-at 500 --output /app/out/traj_full.bin --chk-out /app/out/chk.bin
  nbody restore --scenario /app/data/scenarios/two_body_grazing.icbin --chk /app/out/chk.bin --steps 500 --output /app/out/traj_resumed.bin

The checkpoint format, required fields, CRC contract, and MXCSR requirements are in /app/data/spec/format.md.
