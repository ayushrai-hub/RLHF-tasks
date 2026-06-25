#pragma once

#include <string>
#include <vector>

struct CaseRow {
    std::string id;
    double bias;
    double slope;
};

struct VecPack {
    double local_norm;
    double local_spread;
    int local_count;
};

struct FoldPack {
    double g_norm;
    double g_spread;
    int g_count;
};

struct TraceRow {
    double scalar;
    double dispersion;
    int tick;
};

struct Checkpoint {
    int seed;
    int workers;
    double saved_dispersion;
};