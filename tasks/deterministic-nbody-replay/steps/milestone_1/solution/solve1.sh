#!/bin/bash
# Milestone 1 fix:
#   1. Initialize canonical_index in scenario.cpp body loader loop.
#   2. Remove pointer-comparison fallback from force_kernel.cpp sort comparator.
#   3. Add GCC pragmas to disable fast-math/FMA in force_kernel.cpp.
#   4. Remove -ffast-math from CMakeLists.txt.
#   5. Rebuild and produce two trajectory outputs to verify determinism.
set -euo pipefail

SRC=/app/src

# ---------------------------------------------------------------------------
# Fix 1: scenario.cpp — set canonical_index = i in body loading loop
# ---------------------------------------------------------------------------
python3 - <<'PYEOF'
path = "/app/src/scenario.cpp"
with open(path, "r") as f:
    text = f.read()

old = (
    "        b.active = true;\n"
    "        b._pad[0] = b._pad[1] = b._pad[2] = 0;\n"
    "\n"
    "        // BUG (C5): canonical_index is NOT set here in the starter code.\n"
    "        // It is left uninitialized, so the sort comparator in the force\n"
    "        // kernel reads indeterminate memory and produces non-deterministic\n"
    "        // body ordering.\n"
    "        // b.canonical_index = i;   <-- this line is intentionally omitted\n"
)

new = (
    "        b.active = true;\n"
    "        b._pad[0] = b._pad[1] = b._pad[2] = 0;\n"
    "        b.canonical_index = i;\n"
)

assert old in text, "Expected pattern not found in scenario.cpp — already patched?"
text = text.replace(old, new, 1)
with open(path, "w") as f:
    f.write(text)
print("scenario.cpp: canonical_index initialized.")
PYEOF

# ---------------------------------------------------------------------------
# Fix 2 & 3: force_kernel.cpp — remove pointer fallback, add no-fast-math pragmas
# ---------------------------------------------------------------------------
python3 - <<'PYEOF'
path = "/app/src/force_kernel.cpp"
with open(path, "r") as f:
    text = f.read()

# 2a. Add pragmas at the top of the file (after the existing includes)
pragma_block = (
    '#pragma GCC optimize("no-fast-math", "no-trapping-math")\n'
    '#pragma GCC target("no-fma")\n'
    "\n"
)
# Insert after the last #include line at the top
import re
# Find the position right after the block of includes at the file start
last_include_match = None
for m in re.finditer(r'^#include\s+.*$', text, re.MULTILINE):
    last_include_match = m
assert last_include_match is not None, "No #include lines found in force_kernel.cpp"
insert_pos = last_include_match.end()
text = text[:insert_pos] + "\n" + pragma_block + text[insert_pos:]

# 2b. Fix body_order_less to remove the pointer-comparison fallback
old_comparator = (
    "static bool body_order_less(const Body* a, const Body* b) {\n"
    "    // Primary: canonical_index (uninitialized in starter code — BUG)\n"
    "    if (a->canonical_index != b->canonical_index)\n"
    "        return a->canonical_index < b->canonical_index;\n"
    "    // Fallback: pointer comparison (changes every run — BUG)\n"
    "    return std::less<const Body*>{}(a, b);\n"
    "}"
)
new_comparator = (
    "static bool body_order_less(const Body* a, const Body* b) {\n"
    "    return a->canonical_index < b->canonical_index;\n"
    "}"
)
assert old_comparator in text, (
    "Expected comparator pattern not found in force_kernel.cpp — already patched?"
)
text = text.replace(old_comparator, new_comparator, 1)

with open(path, "w") as f:
    f.write(text)
print("force_kernel.cpp: pointer fallback removed, no-fast-math pragmas added.")
PYEOF

# ---------------------------------------------------------------------------
# Fix 4: CMakeLists.txt — remove -ffast-math flag
# ---------------------------------------------------------------------------
python3 - <<'PYEOF'
path = "/app/CMakeLists.txt"
with open(path, "r") as f:
    text = f.read()

old = 'set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O2 -ffast-math -march=native")'
new = 'set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O2 -march=native")'
assert old in text, "Expected -ffast-math line not found in CMakeLists.txt — already patched?"
text = text.replace(old, new, 1)
with open(path, "w") as f:
    f.write(text)
print("CMakeLists.txt: -ffast-math removed.")
PYEOF

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
mkdir -p /app/build
cd /app/build
cmake /app -DCMAKE_BUILD_TYPE=Release
make -j"$(nproc)"
echo "Build succeeded."

# ---------------------------------------------------------------------------
# Produce outputs
# ---------------------------------------------------------------------------
mkdir -p /app/out

/app/build/nbody run \
    --scenario /app/data/scenarios/two_body_grazing.icbin \
    --steps 1000 \
    --output /app/out/traj.bin

/app/build/nbody run \
    --scenario /app/data/scenarios/two_body_grazing.icbin \
    --steps 1000 \
    --output /app/out/traj2.bin

echo "traj.bin and traj2.bin produced."

# Verify byte-identical (quick sanity check)
if cmp -s /app/out/traj.bin /app/out/traj2.bin; then
    echo "PASS: traj.bin and traj2.bin are byte-identical."
else
    echo "FAIL: traj.bin and traj2.bin differ — fix did not achieve determinism." >&2
    exit 1
fi
