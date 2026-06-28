# Offline firmware build workspace

The tree under `/app/environment` is a small CMake-driven C workspace with three policy modules (`q4`, `w7`, `p2`), shared widget sources, two link targets, and host tools in `bin/` after build.

Object files and linked binaries live under `/app/environment/var/`. The generated constants header is rendered from `data/gen/version_slot.h.in` into `var/gen/version_slot.h`.
