#include "force_kernel.hpp"
#include <algorithm>
#include <cmath>
#include <functional>

static bool body_order_less(const Body* a, const Body* b) {
    // Primary: canonical_index (uninitialized in starter code — BUG)
    if (a->canonical_index != b->canonical_index)
        return a->canonical_index < b->canonical_index;
    // Fallback: pointer comparison (changes every run — BUG)
    return std::less<const Body*>{}(a, b);
}

void compute_forces(std::vector<Body>& bodies, double G, double softening2) {
    const int n = static_cast<int>(bodies.size());

    // Zero accelerations
    for (auto& b : bodies) {
        b.ax = b.ay = b.az = 0.0;
    }

    // Build pointer array and sort to determine accumulation order.
    std::vector<Body*> order;
    order.reserve(n);
    for (auto& b : bodies) order.push_back(&b);
    std::sort(order.begin(), order.end(), body_order_less);

    // Pairwise accumulation in sorted order.
    for (int i = 0; i < n; ++i) {
        Body* bi = order[i];
        if (!bi->active) continue;
        for (int j = i + 1; j < n; ++j) {
            Body* bj = order[j];
            if (!bj->active) continue;

            double dx = bj->x - bi->x;
            double dy = bj->y - bi->y;
            double dz = bj->z - bi->z;

            double r2 = dx * dx + dy * dy + dz * dz + softening2;
            double inv_r  = 1.0 / std::sqrt(r2);
            double inv_r3 = inv_r * inv_r * inv_r;

            double fx = G * bj->mass * dx * inv_r3;
            double fy = G * bj->mass * dy * inv_r3;
            double fz = G * bj->mass * dz * inv_r3;

            bi->ax += fx;
            bi->ay += fy;
            bi->az += fz;

            bj->ax -= G * bi->mass * dx * inv_r3;
            bj->ay -= G * bi->mass * dy * inv_r3;
            bj->az -= G * bi->mass * dz * inv_r3;
        }
    }
}
