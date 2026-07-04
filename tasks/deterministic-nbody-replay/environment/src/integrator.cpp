#include "integrator.hpp"
#include "force_kernel.hpp"
#include "serialization.hpp"
#include <cstdint>
#include <cstdio>
#include <cstring>

static void write_traj_step(FILE* f, const std::vector<Body>& bodies,
                            uint64_t step) {
    if (!f) return;
    fwrite(&step, sizeof(step), 1, f);
    for (const auto& b : bodies) {
        fwrite(&b.x,  sizeof(double), 1, f);
        fwrite(&b.y,  sizeof(double), 1, f);
        fwrite(&b.z,  sizeof(double), 1, f);
        fwrite(&b.vx, sizeof(double), 1, f);
        fwrite(&b.vy, sizeof(double), 1, f);
        fwrite(&b.vz, sizeof(double), 1, f);
    }
}

static inline void kahan_add(double& sum, double& comp, double addend) {
    double y = addend - comp;
    double t = sum + y;
    comp = (t - sum) - y;
    sum = t;
}

void init_half_step(std::vector<Body>& bodies, const ScenarioParams& params) {
    compute_forces(bodies, params.G, params.softening2);
    const double half_dt = 0.5 * params.dt;
    for (auto& b : bodies) {
        b.vhx = b.vx + half_dt * b.ax;
        b.vhy = b.vy + half_dt * b.ay;
        b.vhz = b.vz + half_dt * b.az;
    }
}

bool run_integration(std::vector<Body>& bodies,
                     const ScenarioParams& params,
                     uint64_t start_step,
                     uint64_t num_steps,
                     FILE* traj_out,
                     FILE* chk_out,
                     uint64_t chk_step) {
    const double dt       = params.dt;
    const double half_dt  = 0.5 * dt;
    const double G        = params.G;
    const double soft2    = params.softening2;

    // Write the initial state as step 0 if starting from scratch
    if (start_step == 0) {
        write_traj_step(traj_out, bodies, 0);
    }

    for (uint64_t s = 0; s < num_steps; ++s) {
        const uint64_t current_step = start_step + s;

        // Drift: x += vhx * dt  (Kahan compensated)
        for (auto& b : bodies) {
            if (!b.active) continue;
            kahan_add(b.x, b.kc_x, b.vhx * dt);
            kahan_add(b.y, b.kc_y, b.vhy * dt);
            kahan_add(b.z, b.kc_z, b.vhz * dt);
        }

        // Force computation at new positions
        compute_forces(bodies, G, soft2);

        // Second half-kick: integer-step velocity
        // Update half-step carry for the next iteration
        for (auto& b : bodies) {
            if (!b.active) continue;
            b.vx = b.vhx + half_dt * b.ax;
            b.vy = b.vhy + half_dt * b.ay;
            b.vz = b.vhz + half_dt * b.az;
            b.vhx = b.vx + half_dt * b.ax;
            b.vhy = b.vy + half_dt * b.ay;
            b.vhz = b.vz + half_dt * b.az;
        }

        const uint64_t new_step = current_step + 1;
        write_traj_step(traj_out, bodies, new_step);

        // Checkpoint at the requested step
        if (chk_out && new_step == chk_step) {
            if (!write_checkpoint(chk_out, bodies, new_step)) return false;
        }
    }
    return true;
}
