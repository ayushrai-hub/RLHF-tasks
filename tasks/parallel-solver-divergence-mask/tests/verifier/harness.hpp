#pragma once

#include "contract_model.hpp"

#include <cstdint>
#include <string>
#include <utility>
#include <vector>

struct RunOutputs {
    std::vector<std::pair<std::string, double>> assets;
    double objective;
    int seed;
    int workers;
    std::string mode;
    int phase_id;
    std::string fold_token;
    double dispersion_score;
    std::string audit_chain;
    std::string report_blob;
};

void rebuild_agent_binary();
int run_tb_iter(
    const std::string& out_dir,
    int workers,
    int seed,
    const std::string& mode,
    const std::string& save_path,
    const std::string& load_path,
    const std::string& layout_path,
    const std::string& journal_path);
RunOutputs read_run_outputs(
    const std::string& out_dir,
    int seed,
    int workers,
    const std::string& mode,
    int expected_phase_id);
void assert_assets_close(
    const std::vector<std::pair<std::string, double>>& got,
    const std::vector<std::pair<std::string, double>>& exp,
    double tol,
    const std::string& label);
void assert_full_contract(
    int seed,
    const RunOutputs& got,
    int workers,
    const std::string& mode,
    int phase_id);
std::string sha256_file(const std::string& path);
std::string read_text_file(const std::string& path);
void reset_journal(const std::string& path);
