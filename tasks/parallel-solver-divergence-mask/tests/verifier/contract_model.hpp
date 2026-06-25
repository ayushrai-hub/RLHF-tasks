#pragma once

#include <cstdint>
#include <string>
#include <utility>
#include <vector>

struct CaseRow {
    std::string id;
    double bias;
    double slope;
};

struct ExpectedReport {
    std::vector<std::pair<std::string, double>> assets;
    double objective;
};

std::vector<CaseRow> case_rows();
double mix_value(int seed, int index);
std::vector<double> expected_values(int seed);
double expected_dispersion(int seed);
ExpectedReport expected_report(int seed);
std::string expected_fold_token(int seed);
std::string expected_audit_chain(int seed);

extern const int kHardSeeds[];
extern const int kHardSeedCount;
extern const int kFullSweepSeeds[];
extern const int kFullSweepSeedCount;
extern const int kPrecisionEdgeSeeds[];
extern const int kPrecisionEdgeSeedCount;
extern const int kContinueSeeds[];
extern const int kContinueSeedCount;
extern const int kLaneCoverSeeds[];
extern const int kLaneCoverSeedCount;
extern const int kDispersionFormulaSeeds[];
extern const int kDispersionFormulaSeedCount;
