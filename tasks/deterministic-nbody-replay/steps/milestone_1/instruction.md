We have a direct-summation N-body integrator in /app/src that's supposed to be deterministic, but two back-to-back runs of the grazing scenario produce different binary dumps. The engine builds with /app/CMakeLists.txt; the binary format and integration contract are defined in /app/data/spec/format.md.

Build the binary first (cmake + make), then run: `nbody run --scenario /app/data/scenarios/two_body_grazing.icbin --steps 1000 --output /app/out/traj.bin` and make two consecutive uninterrupted runs produce byte-identical output at /app/out/traj.bin and /app/out/traj2.bin. Do not change the physics, the scenario constants (G, dt, softening), or the output format.

The output must conform exactly to format.md — including the correct record count (one record for each step from 0 through N inclusive), correct step counter values at every record, and the scenario file's header fields parsed as their declared unsigned types. The grazing trajectory's velocity values must remain physically sensible and nonzero throughout the run.

There is a note about an unusual value in the grazing run at /app/data/expected/energy_note.txt — read it before touching anything in that neighborhood.
