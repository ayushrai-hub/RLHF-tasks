Use the three-body scenario at /app/data/scenarios/three_body_activated.icbin. The third body is inert until a specific step; the activation step is encoded in the file per /app/data/spec/format.md.

Run the scenario from scratch to step 1000 as the reference, then take a checkpoint before the third body activates, restore it, and run to the same horizon. The extended run must match the reference byte-for-byte from the checkpoint step onward.

  nbody run     --scenario /app/data/scenarios/three_body_activated.icbin --steps 1000 --output /app/out/traj_full3.bin
  nbody chkpt   --scenario /app/data/scenarios/three_body_activated.icbin --steps 1000 --chk-at 100 --output /app/out/traj_pre3.bin --chk-out /app/out/chk3.bin
  nbody extend  --scenario /app/data/scenarios/three_body_activated.icbin --chk /app/out/chk3.bin --steps 900 --output /app/out/extended.bin

The force reduction order for body activation and the handling of the activation gap are specified in /app/data/spec/format.md. All guarantees from the previous milestones must still hold.

The inactive body's position must remain completely frozen in the full-run trajectory until its activation step — this must be directly observable in traj_full3.bin. The step-gap arithmetic between the checkpoint step and the activation step must use unsigned arithmetic; a checkpoint taken at step 0 followed by extend to the full horizon must work correctly without any wraparound.
