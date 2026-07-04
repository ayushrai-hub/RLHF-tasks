#include "body.hpp"
#include "force_kernel.hpp"
#include "integrator.hpp"
#include "scenario.hpp"
#include "serialization.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <cmath>
#include <xmmintrin.h>
#include <pmmintrin.h>

static ScenarioParams g_params;

static void usage(const char* prog) {
    fprintf(stderr,
        "Usage:\n"
        "  %s run     --scenario FILE --steps N --output FILE\n"
        "  %s chkpt   --scenario FILE --steps N --chk-at K "
                     "--output FILE --chk-out FILE\n"
        "  %s restore --scenario FILE --chk FILE --steps N --output FILE\n"
        "  %s extend  --scenario FILE --chk FILE --steps N "
                     "--output FILE [--chk-out FILE]\n",
        prog, prog, prog, prog);
}

static void ensure_dir(const std::string& path) {
    size_t pos = path.rfind('/');
    if (pos != std::string::npos) {
        std::string cmd = "mkdir -p " + path.substr(0, pos);
        (void)system(cmd.c_str());
    }
}

static FILE* open_output(const std::string& path) {
    if (path.empty()) return nullptr;
    ensure_dir(path);
    FILE* f = fopen(path.c_str(), "wb");
    if (!f) { perror(path.c_str()); }
    return f;
}

static void activate_body(std::vector<Body>& bodies, int idx,
                           const ScenarioParams& params) {
    Body& b = bodies[static_cast<size_t>(idx)];
    b.active = true;

    // BUG: calling full compute_forces() recalculates ALL bodies' accelerations,
    // disrupting the mid-step state of bodies 0 and 1. It also uses the sort
    // order (non-canonical if indices uninitialized). A correct implementation
    // computes only the acceleration OF body idx from all others in ascending
    // canonical index order.
    compute_forces(bodies, params.G, params.softening2);

    // BUG (C16): activation_step and chk_step are both uint64_t here, but in
    // an incorrect implementation the gap arithmetic might use int32_t, causing
    // signed overflow or truncation for large step counts.
    uint64_t chk_step = 0; // placeholder — in restore-act path this should be set
    uint64_t gap = params.activation_step - chk_step; // potentially wrong type
    (void)gap;

    double half_dt = 0.5 * params.dt;
    b.vhx = b.vx + half_dt * b.ax;
    b.vhy = b.vy + half_dt * b.ay;
    b.vhz = b.vz + half_dt * b.az;
}

// Run integration with activation support.
// Mirrors run_integration() but checks for body activation at each step.
// emit_initial controls whether the step-0 record is written to traj_out.
// Pass true for fresh 'run'/'chkpt' invocations; pass false for 'extend'
// so the output starts at step start_step+1 (matching restore semantics).
static bool run_integration_act(std::vector<Body>& bodies,
                                 const ScenarioParams& params,
                                 uint64_t start_step,
                                 uint64_t num_steps,
                                 FILE* traj_out,
                                 FILE* chk_out,
                                 uint64_t chk_step_val,
                                 FILE* chk_out2,
                                 bool emit_initial = true) {
    const double dt      = params.dt;
    const double half_dt = 0.5 * dt;

    if (start_step == 0) {
        // Write initial step-0 state only for fresh runs, not for extend.
        if (emit_initial && traj_out) {
            uint64_t step = 0;
            fwrite(&step, sizeof(step), 1, traj_out);
            for (const auto& b : bodies) {
                fwrite(&b.x,  8, 1, traj_out);
                fwrite(&b.y,  8, 1, traj_out);
                fwrite(&b.z,  8, 1, traj_out);
                fwrite(&b.vx, 8, 1, traj_out);
                fwrite(&b.vy, 8, 1, traj_out);
                fwrite(&b.vz, 8, 1, traj_out);
            }
        }
        // Checkpoint at step 0 must be written BEFORE the first integration
        // step, since new_step starts at 1 inside the loop and would never
        // match chk_step_val == 0.
        if (chk_step_val == 0) {
            if (chk_out)  write_checkpoint(chk_out,  bodies, 0);
            if (chk_out2) write_checkpoint(chk_out2, bodies, 0);
        }
    }

    for (uint64_t s = 0; s < num_steps; ++s) {
        const uint64_t current_step = start_step + s;

        // Check activation
        if (params.activation_body_index >= 0 &&
            !bodies[static_cast<size_t>(params.activation_body_index)].active &&
            current_step + 1 == params.activation_step) {
            activate_body(bodies, params.activation_body_index, params);
        }

        // Drift
        for (auto& b : bodies) {
            if (!b.active) continue;
            double y_x = b.vhx * dt - b.kc_x;
            double t_x = b.x + y_x;
            b.kc_x = (t_x - b.x) - y_x;
            b.x = t_x;

            double y_y = b.vhy * dt - b.kc_y;
            double t_y = b.y + y_y;
            b.kc_y = (t_y - b.y) - y_y;
            b.y = t_y;

            double y_z = b.vhz * dt - b.kc_z;
            double t_z = b.z + y_z;
            b.kc_z = (t_z - b.z) - y_z;
            b.z = t_z;
        }

        compute_forces(bodies, params.G, params.softening2);

        for (auto& b : bodies) {
            if (!b.active) continue;
            b.vx  = b.vhx + half_dt * b.ax;
            b.vy  = b.vhy + half_dt * b.ay;
            b.vz  = b.vhz + half_dt * b.az;
            b.vhx = b.vx  + half_dt * b.ax;
            b.vhy = b.vy  + half_dt * b.ay;
            b.vhz = b.vz  + half_dt * b.az;
        }

        const uint64_t new_step = current_step + 1;
        if (traj_out) {
            fwrite(&new_step, sizeof(new_step), 1, traj_out);
            for (const auto& b : bodies) {
                fwrite(&b.x,  8, 1, traj_out);
                fwrite(&b.y,  8, 1, traj_out);
                fwrite(&b.z,  8, 1, traj_out);
                fwrite(&b.vx, 8, 1, traj_out);
                fwrite(&b.vy, 8, 1, traj_out);
                fwrite(&b.vz, 8, 1, traj_out);
            }
        }

        if (chk_out && new_step == chk_step_val) {
            write_checkpoint(chk_out, bodies, new_step);
        }
        if (chk_out2 && new_step == chk_step_val) {
            write_checkpoint(chk_out2, bodies, new_step);
        }
    }
    return true;
}

int main(int argc, char** argv) {
    if (argc < 2) { usage(argv[0]); return 1; }

    std::string mode = argv[1];

    // FTZ/DAZ for fresh runs.
    if (mode == "run" || mode == "chkpt") {
        _MM_SET_FLUSH_ZERO_MODE(_MM_FLUSH_ZERO_ON);
        _MM_SET_DENORMALS_ZERO_MODE(_MM_DENORMALS_ZERO_ON);
    }
    std::string scenario_path, output_path, chk_path, chk_out_path;
    uint64_t num_steps = 1000;
    uint64_t chk_at    = 500;

    for (int i = 2; i < argc; ++i) {
        std::string flag = argv[i];
        if ((flag == "--scenario" || flag == "--scen") && i+1 < argc) scenario_path = argv[++i];
        else if (flag == "--steps" && i+1 < argc) num_steps = strtoull(argv[++i], nullptr, 10);
        else if (flag == "--chk-at" && i+1 < argc) chk_at = strtoull(argv[++i], nullptr, 10);
        else if (flag == "--output" && i+1 < argc) output_path = argv[++i];
        else if (flag == "--chk-out" && i+1 < argc) chk_out_path = argv[++i];
        else if (flag == "--chk" && i+1 < argc) chk_path = argv[++i];
    }

    if (mode == "run" || mode == "chkpt") {
        if (scenario_path.empty()) { usage(argv[0]); return 1; }
        std::vector<Body> bodies;
        if (!load_scenario(scenario_path, bodies, g_params)) {
            fprintf(stderr, "load_scenario failed: %s\n", scenario_path.c_str());
            return 1;
        }

        FILE* out  = open_output(output_path);
        FILE* chkf = nullptr;
        if (mode == "chkpt") chkf = open_output(chk_out_path);

        init_half_step(bodies, g_params);
        run_integration(bodies, g_params, 0, num_steps, out, chkf, chk_at);

        if (out)  fclose(out);
        if (chkf) fclose(chkf);
        return 0;
    }

    if (mode == "restore") {
        if (chk_path.empty() || scenario_path.empty()) { usage(argv[0]); return 1; }

        // Load scenario params (needed for dt, G, softening2)
        std::vector<Body> dummy;
        if (!load_scenario(scenario_path, dummy, g_params)) {
            fprintf(stderr, "load_scenario failed\n"); return 1;
        }

        std::vector<Body> bodies;
        uint64_t start_step = 0;
        if (!read_checkpoint(chk_path, bodies, start_step)) {
            fprintf(stderr, "read_checkpoint failed: %s\n", chk_path.c_str());
            return 1;
        }
        // BUG: vhx is zero (not saved in checkpoint), so we must recompute.
        // init_half_step calls compute_forces, which is sensitive to MXCSR.
        init_half_step(bodies, g_params);

        FILE* out = open_output(output_path);
        run_integration(bodies, g_params, start_step, num_steps, out, nullptr, 0);
        if (out) fclose(out);
        return 0;
    }

    if (mode == "extend") {
        // M3: restore from pre-activation checkpoint, run with activation handling
        if (chk_path.empty() || scenario_path.empty()) { usage(argv[0]); return 1; }

        std::vector<Body> dummy;
        if (!load_scenario(scenario_path, dummy, g_params)) {
            fprintf(stderr, "load_scenario failed\n"); return 1;
        }

        std::vector<Body> bodies;
        uint64_t start_step = 0;
        if (!read_checkpoint(chk_path, bodies, start_step)) {
            fprintf(stderr, "read_checkpoint failed\n"); return 1;
        }

        // Restore body activation flags from scenario (not saved in checkpoint)
        for (size_t i = 0; i < bodies.size() && i < dummy.size(); ++i) {
            bodies[i].active = dummy[i].active;
        }
        // Re-apply scenario activation: if activation_step > start_step, body is still inert
        if (g_params.activation_body_index >= 0) {
            bool still_inert = (start_step < g_params.activation_step);
            bodies[static_cast<size_t>(g_params.activation_body_index)].active = !still_inert;
        }

        init_half_step(bodies, g_params);  // BUG: vhx missing, same as restore

        FILE* out   = open_output(output_path);
        FILE* chkf2 = open_output(chk_out_path);

        // emit_initial=false: extend output starts at start_step+1, not start_step.
        run_integration_act(bodies, g_params, start_step, num_steps,
                            out, nullptr, 0, chkf2, false);

        if (out)   fclose(out);
        if (chkf2) fclose(chkf2);
        return 0;
    }

    usage(argv[0]);
    return 1;
}
