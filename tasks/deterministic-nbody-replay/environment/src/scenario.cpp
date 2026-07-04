#include "scenario.hpp"
#include <cstdio>
#include <cstring>

static bool read_exact(FILE* f, void* buf, size_t n) {
    return fread(buf, 1, n, f) == n;
}

static double read_le_double(FILE* f, bool& ok) {
    uint64_t raw = 0;
    if (!read_exact(f, &raw, 8)) { ok = false; return 0.0; }
    double v;
    memcpy(&v, &raw, 8);
    return v;
}

static uint64_t read_le_u64(FILE* f, bool& ok) {
    uint64_t v = 0;
    if (!read_exact(f, &v, 8)) { ok = false; return 0; }
    return v;
}

static int32_t read_le_i32(FILE* f, bool& ok) {
    int32_t v = 0;
    if (!read_exact(f, &v, 4)) { ok = false; return 0; }
    return v;
}

bool load_scenario(const std::string& path,
                   std::vector<Body>& bodies,
                   ScenarioParams& params) {
    FILE* f = fopen(path.c_str(), "rb");
    if (!f) return false;

    char magic[4] = {};
    if (!read_exact(f, magic, 4)) { fclose(f); return false; }
    if (memcmp(magic, "NBIC", 4) != 0) { fclose(f); return false; }

    char version_raw = 0, dim_raw = 0;
    if (!read_exact(f, &version_raw, 1)) { fclose(f); return false; }
    if (!read_exact(f, &dim_raw, 1)) { fclose(f); return false; }
    params.version = static_cast<uint8_t>(version_raw);
    params.dim     = static_cast<uint8_t>(dim_raw);

    bool ok = true;
    params.body_count = read_le_i32(f, ok);
    params.dt         = read_le_double(f, ok);
    params.softening2 = read_le_double(f, ok);
    params.G          = read_le_double(f, ok);
    params.seed       = read_le_u64(f, ok);
    if (!ok || params.body_count <= 0 || params.body_count > 1024) {
        fclose(f); return false;
    }

    bodies.resize(static_cast<size_t>(params.body_count));
    for (int i = 0; i < params.body_count; ++i) {
        Body& b = bodies[i];
        b.mass = read_le_double(f, ok);
        b.x    = read_le_double(f, ok);
        b.y    = read_le_double(f, ok);
        b.z    = read_le_double(f, ok);
        b.vx   = read_le_double(f, ok);
        b.vy   = read_le_double(f, ok);
        b.vz   = read_le_double(f, ok);

        b.vhx = b.vhy = b.vhz = 0.0;
        b.kc_x = b.kc_y = b.kc_z = 0.0;
        b.ax = b.ay = b.az = 0.0;
        b.active = true;
        b._pad[0] = b._pad[1] = b._pad[2] = 0;

        // BUG (C5): canonical_index is NOT set here in the starter code.
        // It is left uninitialized, so the sort comparator in the force
        // kernel reads indeterminate memory and produces non-deterministic
        // body ordering.
        // b.canonical_index = i;   <-- this line is intentionally omitted
    }

    // Try to read an activation record (only present in three-body scenario)
    params.activation_body_index = -1;
    int32_t act_body = 0;
    uint64_t act_step = 0;
    if (fread(&act_body, 4, 1, f) == 1 && fread(&act_step, 8, 1, f) == 1) {
        params.activation_body_index = act_body;
        params.activation_step = act_step;
        if (act_body >= 0 && act_body < params.body_count) {
            bodies[act_body].active = false;
        }
    }

    fclose(f);
    return ok;
}
