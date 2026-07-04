# N-Body Binary Format Specification

All multi-byte integers and floating-point values are **little-endian**.

---

## Scenario File (.icbin)

Header (fixed layout, no padding between fields):

| Offset | Size | Type     | Field         |
|--------|------|----------|---------------|
| 0      | 4    | char[4]  | magic = "NBIC"|
| 4      | 1    | uint8    | version = 1   |
| 5      | 1    | uint8    | dim = 3       |
| 6      | 4    | int32    | body_count    |
| 10     | 8    | double   | dt            |
| 18     | 8    | double   | softening2    |
| 26     | 8    | double   | G             |
| 34     | 8    | uint64   | seed          |

Followed by `body_count` body records (no padding):

| Size | Type   | Field |
|------|--------|-------|
| 8    | double | mass  |
| 8    | double | x     |
| 8    | double | y     |
| 8    | double | z     |
| 8    | double | vx    |
| 8    | double | vy    |
| 8    | double | vz    |

For `three_body_activated.icbin`, after all body records, one activation record:

| Size | Type   | Field          |
|------|--------|----------------|
| 4    | int32  | body_index     |
| 8    | uint64 | activation_step|

The body at `body_index` is inert (contributes zero force, position frozen) until step `activation_step`.

---

## Trajectory Dump (.traj)

One record per step, for steps 0 through N inclusive (N+1 records total for an N-step run):

| Size | Type   | Field    |
|------|--------|----------|
| 8    | uint64 | step     |

Then for each body in ascending canonical index order (0 to body_count-1):

| Size | Type   | Field |
|------|--------|-------|
| 8    | double | x     |
| 8    | double | y     |
| 8    | double | z     |
| 8    | double | vx    |
| 8    | double | vy    |
| 8    | double | vz    |

No padding. No header. Records are contiguous.

---

## Checkpoint File (.chk)

Header:

| Offset | Size | Type    | Field              |
|--------|----|---------|----------------------|
| 0      | 4  | char[4] | magic = "NBCK"       |
| 4      | 1  | uint8   | version = 1          |
| 5      | 4  | int32   | body_count           |
| 9      | 8  | uint64  | step                 |
| 17     | 4  | uint32  | mxcsr                |

Followed by `body_count` body state records:

| Size | Type   | Field  | Description                          |
|------|--------|--------|--------------------------------------|
| 8    | double | x      | position                             |
| 8    | double | y      |                                      |
| 8    | double | z      |                                      |
| 8    | double | vx     | integer-step velocity                |
| 8    | double | vy     |                                      |
| 8    | double | vz     |                                      |
| 8    | double | vhx    | half-step velocity carry             |
| 8    | double | vhy    |                                      |
| 8    | double | vhz    |                                      |
| 8    | double | kc_x   | Kahan compensation for x position    |
| 8    | double | kc_y   |                                      |
| 8    | double | kc_z   |                                      |

Followed by a 4-byte CRC32 (ISO 3309 polynomial) over the canonical payload.

**Canonical payload** for CRC32 is the checkpoint file bytes from the start of the header through the last body state record, with the mxcsr field included. No padding bytes are ever present because the header and body records are written field-by-field in the order above.

---

## Force Reduction Order

Pairwise forces must be accumulated in **strictly ascending body canonical-index order**:

```
for i in 0 .. body_count-1:
    for j in i+1 .. body_count-1:
        compute_pair_force(body[i], body[j])
        body[i].a += contribution_from_j
        body[j].a -= contribution_from_j  (Newton's 3rd law)
```

The Plummer-softened kernel for pair (i, j):

```
dx = x[j] - x[i]
dy = y[j] - y[i]
dz = z[j] - z[i]
r2 = dx*dx + dy*dy + dz*dz + softening2
inv_r  = 1.0 / sqrt(r2)
inv_r3 = inv_r * inv_r * inv_r
a[i].x += G * mass[j] * dx * inv_r3
a[i].y += G * mass[j] * dy * inv_r3
a[i].z += G * mass[j] * dz * inv_r3
a[j].x -= G * mass[i] * dx * inv_r3
a[j].y -= G * mass[i] * dy * inv_r3
a[j].z -= G * mass[i] * dz * inv_r3
```

No FMA contraction is permitted in the above kernel. Each multiply and add must be a distinct IEEE 754 operation.

---

## Integrator Contract (KDK Leapfrog)

At step 0, after reading initial conditions, compute accelerations then initialize the half-step velocity carry:

```
vhx[i] = vx[i] + 0.5 * dt * ax[i]
```

Each subsequent step N → N+1:

1. Drift with Kahan compensation:
   ```
   y = vhx[i] * dt - kc_x[i]
   t = x[i] + y
   kc_x[i] = (t - x[i]) - y
   x[i] = t
   ```
2. Compute forces at new positions → ax[i].
3. Integer-step velocity:
   ```
   vx[i] = vhx[i] + 0.5 * dt * ax[i]
   ```
4. Update half-step carry for next step:
   ```
   vhx[i] = vx[i] + 0.5 * dt * ax[i]
   ```
   (equivalently: vhx[i] += ax[i] * dt)

Record the step (step counter, then positions and integer-step velocities for all bodies) after step 4.

---

## MXCSR / FTZ Contract

The process must enable Flush-To-Zero (FTZ) and Denormals-Are-Zero (DAZ) via the MXCSR register before the first force computation and maintain this mode for the entire run. On checkpoint restore, the MXCSR value stored in the checkpoint header must be loaded into the MXCSR register before resuming integration.

The canonical MXCSR value with FTZ and DAZ enabled is `0x9FC0` (bits 15 and 6 set, plus default rounding and exception masks). The saved mxcsr field in the checkpoint must equal the value returned by `_mm_getcsr()` after startup initialization.

---

## Checkpoint Step

The default checkpoint step for `two_body_grazing.icbin` is **step 500**.
The default checkpoint step for `three_body_activated.icbin` is **step 100** (before the third body activates at step 200).
The default run horizon for all scenarios is **step 1000**.
