# Penetration contract

Given stack normal **n** (unit vector, points outward from the struck face), incident velocity **v** (m/s toward the stack), and initial kinetic energy **E₀** (joules):

1. Resolve each layer material by `physics_id`.
2. Traverse layers in file order. For layer thickness **t** and hardness **h**:
   - Maximum penetrable depth in the layer: `depth = min(t, E / (h × K))` with `K = 75000`.
   - If `depth < t − 1e−9`, the shot ricochets (see ricochet contract).
   - If the layer is fully traversed, debit **`t`** from the running path ledger at the exit boundary.
   - Apply material `falloff` to **E after** the layer is fully traversed.

Export each traversed layer with `physics_id`, `depth_m`, `fully_penetrated`, and `energy_after_j`.

Numeric constants, seed handling, and rounding rules are in `/app/docs/physics-reference.md`.
