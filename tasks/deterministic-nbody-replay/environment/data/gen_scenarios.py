#!/usr/bin/env python3
"""Generate deterministic binary scenario files for the n-body reproducibility task."""

import struct
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), "scenarios")
os.makedirs(OUT_DIR, exist_ok=True)

MAGIC_IC = b"NBIC"
VERSION = 1
DIM = 3


def write_header(f, body_count, dt, softening2, G, seed):
    f.write(MAGIC_IC)
    f.write(struct.pack("<BB", VERSION, DIM))
    f.write(struct.pack("<i", body_count))
    f.write(struct.pack("<dddQ", dt, softening2, G, seed))


def write_body(f, mass, x, y, z, vx, vy, vz):
    f.write(struct.pack("<ddddddd", mass, x, y, z, vx, vy, vz))


# ---- two_body_grazing.icbin ------------------------------------------------
# Two bodies on a close-approach (grazing) orbit.
# Body 0: heavy central body.
# Body 1: light flyby.
#
# Parameters chosen so that at encounter time (around step 500) the relative
# separation components produce denormal intermediate values when squared in
# the force kernel with standard IEEE 754 double arithmetic. Specifically, at
# the initial configuration the y-component of body 1 is set to a value such
# that (y1 - y0)^2 = 2.0e-309 which is a denormal double (below DBL_MIN ~
# 2.225e-308). With FTZ enabled this flushes to 0; without FTZ it is kept.
#
# We use a dimensionless unit system with non-standard G to prevent hardcoding.
G_TWO   = 4.302e-3   # non-standard dimensionless G
DT_TWO  = 5.0e-4
SOFT2   = 1.0e-12
SEED_TWO = 0x5EED_CAFE_1234_5678

# Body 0: unit mass at origin, at rest
M0 = 1.0
X0, Y0, Z0 = 0.0, 0.0, 0.0
VX0, VY0, VZ0 = 0.0, 0.0, 0.0

# Body 1: small mass approaching from +x direction along a slightly off-axis
# trajectory; the y separation is chosen to create a denormal y^2 intermediate.
# y1 = sqrt(2.5e-309) ≈ 5.0e-155 so y1^2 = 2.5e-309 < DBL_MIN (denormal)
M1 = 1.0e-3
X1 = 0.8
Y1 = 5.0e-155   # specifically chosen for denormal y^2 in force kernel
Z1 = 0.0
VX1 = -0.3      # approaching body 0
VY1 = 0.05
VZ1 = 0.0

path_two = os.path.join(OUT_DIR, "two_body_grazing.icbin")
with open(path_two, "wb") as f:
    write_header(f, 2, DT_TWO, SOFT2, G_TWO, SEED_TWO)
    write_body(f, M0, X0, Y0, Z0, VX0, VY0, VZ0)
    write_body(f, M1, X1, Y1, Z1, VX1, VY1, VZ1)

print(f"Written {path_two}")


# ---- three_body_activated.icbin --------------------------------------------
# Three-body scenario with late activation of body 2.
# Bodies 0 and 1 form a stable pair; body 2 is frozen until activation_step.
#
# The activation record instructs the integrator to keep body 2 inert
# (zero force contribution, fixed position) until step activation_step,
# at which point it starts contributing pairwise forces normally.
#
# M3 requires taking a checkpoint BEFORE activation_step, then restoring
# and backfilling the gap forces in canonical index order.
G_THREE   = 4.302e-3
DT_THREE  = 5.0e-4
SOFT2_3   = 1.0e-12
SEED_THREE = 0xABCD_EF01_2345_6789

ACTIVATION_BODY  = 2
ACTIVATION_STEP  = 200   # checkpoint at step 100, horizon at step 1000

# Body 0 and 1: circular-ish orbit
M0_3 = 1.0
X0_3, Y0_3, Z0_3 = 0.5, 0.0, 0.0
VX0_3, VY0_3, VZ0_3 = 0.0, 0.05, 0.0

M1_3 = 1.0
X1_3, Y1_3, Z1_3 = -0.5, 0.0, 0.0
VX1_3, VY1_3, VZ1_3 = 0.0, -0.05, 0.0

# Body 2: distant intruder, initially inactive
M2_3 = 0.01
X2_3, Y2_3, Z2_3 = 5.0, 0.0, 0.0
VX2_3, VY2_3, VZ2_3 = -0.1, 0.0, 0.0

path_three = os.path.join(OUT_DIR, "three_body_activated.icbin")
with open(path_three, "wb") as f:
    write_header(f, 3, DT_THREE, SOFT2_3, G_THREE, SEED_THREE)
    write_body(f, M0_3, X0_3, Y0_3, Z0_3, VX0_3, VY0_3, VZ0_3)
    write_body(f, M1_3, X1_3, Y1_3, Z1_3, VX1_3, VY1_3, VZ1_3)
    write_body(f, M2_3, X2_3, Y2_3, Z2_3, VX2_3, VY2_3, VZ2_3)
    # Activation record
    f.write(struct.pack("<i", ACTIVATION_BODY))
    f.write(struct.pack("<Q", ACTIVATION_STEP))

print(f"Written {path_three}")
print("Scenario generation complete.")
