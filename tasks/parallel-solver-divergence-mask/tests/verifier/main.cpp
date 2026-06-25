#include "harness.hpp"

#include <cctype>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <regex>
#include <sstream>
#include <string>
#include <vector>

namespace {

std::string trim(const std::string& s) {
    size_t b = 0;
    while (b < s.size() && std::isspace(static_cast<unsigned char>(s[b]))) {
        ++b;
    }
    size_t e = s.size();
    while (e > b && std::isspace(static_cast<unsigned char>(s[e - 1]))) {
        --e;
    }
    return s.substr(b, e - b);
}

std::vector<std::string> split_lines(const std::string& text) {
    std::vector<std::string> lines;
    std::istringstream iss(text);
    std::string line;
    while (std::getline(iss, line)) {
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        lines.push_back(line);
    }
    return lines;
}

[[noreturn]] void fail(const std::string& msg) {
    std::cerr << "verifier failure: " << msg << '\n';
    std::exit(1);
}

void ok(const std::string& label) {
    std::cout << "PASS " << label << '\n';
}

void gate_rebuild_agent_binary() {
    rebuild_agent_binary();
    ok("rebuild_agent_binary");
}

void gate_cases_csv_immutable() {
    const std::string doc = read_text_file("/app/docs/report_contract.md");
    const std::regex re("sha256 `([0-9a-f]{64})`");
    std::smatch m;
    if (!std::regex_search(doc, m, re)) {
        fail("cases.csv sha256 missing from report_contract.md");
    }
    const std::string digest = sha256_file("/app/data/cases.csv");
    if (digest != m[1].str()) {
        fail("cases.csv sha256 mismatch");
    }
    ok("cases_csv_immutable");
}

void gate_worker_antipode_blob_lock() {
    rebuild_agent_binary();
    const std::string root = "/tmp/verifier_antipode";
    for (int si = 0; si < kHardSeedCount; ++si) {
        const int seed = kHardSeeds[si];
        const std::string low_out = root + "/lo_" + std::to_string(seed);
        const std::string hi_out = root + "/hi_" + std::to_string(seed);
        if (run_tb_iter(low_out, 2, seed, "fresh", "", "", "", "") != 0) {
            fail("antipode low workers failed seed=" + std::to_string(seed));
        }
        if (run_tb_iter(hi_out, 10, seed, "fresh", "", "", "", "") != 0) {
            fail("antipode high workers failed seed=" + std::to_string(seed));
        }
        const auto lo = read_run_outputs(low_out, seed, 2, "fresh", 0);
        const auto hi = read_run_outputs(hi_out, seed, 10, "fresh", 0);
        assert_full_contract(seed, lo, 2, "fresh", 0);
        assert_full_contract(seed, hi, 10, "fresh", 0);
        if (lo.report_blob != hi.report_blob) {
            fail("report blob drift between workers 2 and 10 seed=" + std::to_string(seed));
        }
        if (lo.fold_token != hi.fold_token || lo.audit_chain != hi.audit_chain) {
            fail("meta drift between workers 2 and 10 seed=" + std::to_string(seed));
        }
    }
    ok("worker_antipode_blob_lock");
}

void gate_lane_cover_shard_matrix() {
    rebuild_agent_binary();
    const std::string root = "/tmp/verifier_lane";
    const int workers[] = {3, 5, 7, 9};
    for (int si = 0; si < kLaneCoverSeedCount; ++si) {
        const int seed = kLaneCoverSeeds[si];
        std::string baseline;
        for (int workers_i : workers) {
            const std::string out = root + "/s" + std::to_string(seed) + "_w" + std::to_string(workers_i);
            if (run_tb_iter(out, workers_i, seed, "fresh", "", "", "", "") != 0) {
                fail("lane cover matrix run failed");
            }
            const auto got = read_run_outputs(out, seed, workers_i, "fresh", 0);
            assert_full_contract(seed, got, workers_i, "fresh", 0);
            if (baseline.empty()) {
                baseline = got.report_blob;
            } else if (got.report_blob != baseline) {
                fail("lane cover report drift seed=" + std::to_string(seed));
            }
        }
    }
    ok("lane_cover_shard_matrix");
}

void gate_parallel_full_contract_worker_sweep() {
    rebuild_agent_binary();
    const std::string root = "/tmp/verifier_full_sweep";
    for (int si = 0; si < kFullSweepSeedCount; ++si) {
        const int seed = kFullSweepSeeds[si];
        for (int workers = 2; workers <= 10; ++workers) {
            const std::string out = root + "/s" + std::to_string(seed) + "_w" + std::to_string(workers);
            if (run_tb_iter(out, workers, seed, "fresh", "", "", "", "") != 0) {
                fail("full contract sweep failed seed=" + std::to_string(seed));
            }
            const auto got = read_run_outputs(out, seed, workers, "fresh", 0);
            assert_full_contract(seed, got, workers, "fresh", 0);
        }
    }
    ok("parallel_full_contract_worker_sweep");
}

void gate_fold_token_exact_precision_sweep() {
    rebuild_agent_binary();
    const std::string root = "/tmp/verifier_fold";
    for (int si = 0; si < kPrecisionEdgeSeedCount; ++si) {
        const int seed = kPrecisionEdgeSeeds[si];
        const std::string expected = expected_fold_token(seed);
        for (int workers = 2; workers <= 10; ++workers) {
            const std::string out = root + "/f_" + std::to_string(seed) + "_" + std::to_string(workers);
            if (run_tb_iter(out, workers, seed, "fresh", "", "", "", "") != 0) {
                fail("tb_iter fold sweep failed");
            }
            const auto got = read_run_outputs(out, seed, workers, "fresh", 0);
            if (got.fold_token != expected) {
                fail("fold_token exact mismatch seed=" + std::to_string(seed));
            }
        }
    }
    ok("fold_token_exact_precision_sweep");
}

void gate_weight_pre_renorm_precision_seeds() {
    rebuild_agent_binary();
    const std::string root = "/tmp/verifier_weight";
    for (int si = 0; si < kPrecisionEdgeSeedCount; ++si) {
        const int seed = kPrecisionEdgeSeeds[si];
        const auto exp = expected_report(seed);
        for (int workers = 2; workers <= 10; ++workers) {
            const std::string out = root + "/w_" + std::to_string(seed) + "_" + std::to_string(workers);
            if (run_tb_iter(out, workers, seed, "fresh", "", "", "", "") != 0) {
                fail("tb_iter weight sweep failed");
            }
            const auto got = read_run_outputs(out, seed, workers, "fresh", 0);
            assert_assets_close(got.assets, exp.assets, 1e-15, "weight_ultra_precision");
        }
    }
    ok("weight_pre_renorm_precision_seeds");
}

void gate_objective_cross_worker_invariance() {
    rebuild_agent_binary();
    const std::string root = "/tmp/verifier_objective";
    for (int si = 0; si < kPrecisionEdgeSeedCount; ++si) {
        const int seed = kPrecisionEdgeSeeds[si];
        const auto exp = expected_report(seed);
        double baseline = 0.0;
        bool have = false;
        for (int workers = 2; workers <= 10; ++workers) {
            const std::string out = root + "/o_" + std::to_string(seed) + "_" + std::to_string(workers);
            if (run_tb_iter(out, workers, seed, "fresh", "", "", "", "") != 0) {
                fail("objective sweep failed");
            }
            const auto got = read_run_outputs(out, seed, workers, "fresh", 0);
            if (std::abs(got.objective - exp.objective) > 1e-9) {
                fail("objective contract mismatch seed=" + std::to_string(seed));
            }
            if (!have) {
                baseline = got.objective;
                have = true;
            } else if (std::abs(got.objective - baseline) > 1e-12) {
                fail("objective drift across workers seed=" + std::to_string(seed));
            }
        }
    }
    ok("objective_cross_worker_invariance");
}

void gate_audit_chain_antipode_lock() {
    rebuild_agent_binary();
    const std::string root = "/tmp/verifier_audit_antipode";
    for (int si = 0; si < kHardSeedCount; ++si) {
        const int seed = kHardSeeds[si];
        const std::string low_out = root + "/lo_" + std::to_string(seed);
        const std::string hi_out = root + "/hi_" + std::to_string(seed);
        if (run_tb_iter(low_out, 2, seed, "fresh", "", "", "", "") != 0) {
            fail("audit antipode low workers failed");
        }
        if (run_tb_iter(hi_out, 10, seed, "fresh", "", "", "", "") != 0) {
            fail("audit antipode high workers failed");
        }
        const auto lo = read_run_outputs(low_out, seed, 2, "fresh", 0);
        const auto hi = read_run_outputs(hi_out, seed, 10, "fresh", 0);
        const std::string expected_chain = expected_audit_chain(seed);
        if (lo.audit_chain != expected_chain || hi.audit_chain != expected_chain) {
            fail("audit_chain contract mismatch seed=" + std::to_string(seed));
        }
        if (lo.audit_chain != hi.audit_chain || lo.report_blob != hi.report_blob) {
            fail("audit antipode drift seed=" + std::to_string(seed));
        }
    }
    ok("audit_chain_antipode_lock");
}

void gate_continue_fresh_parity_with_journal() {
    rebuild_agent_binary();
    const std::string root = "/tmp/verifier_cont_journal";
    for (int si = 0; si < kContinueSeedCount; ++si) {
        const int seed = kContinueSeeds[si];
        const int workers = 4;
        const std::string journal = root + "/j_" + std::to_string(seed) + ".journal";
        const std::string save = root + "/cp_" + std::to_string(seed) + ".cp";
        const std::string fresh_out = root + "/fresh_" + std::to_string(seed);
        const std::string cont_out = root + "/cont_" + std::to_string(seed);
        std::filesystem::create_directories(root);
        reset_journal(journal);
        if (run_tb_iter(fresh_out, workers, seed, "fresh", save, "", "", journal) != 0) {
            fail("fresh save with journal failed");
        }
        if (run_tb_iter(cont_out, workers, seed, "continued", "", save, "", journal) != 0) {
            fail("continued load with journal failed");
        }
        const auto fresh = read_run_outputs(fresh_out, seed, workers, "fresh", 0);
        const auto cont = read_run_outputs(cont_out, seed, workers, "continued", 1);
        assert_full_contract(seed, fresh, workers, "fresh", 0);
        assert_full_contract(seed, cont, workers, "continued", 1);
        if (fresh.report_blob != cont.report_blob) {
            fail("continued report differs from fresh seed=" + std::to_string(seed));
        }
        if (fresh.fold_token != cont.fold_token || fresh.dispersion_score != cont.dispersion_score) {
            fail("continued meta differs from fresh seed=" + std::to_string(seed));
        }
        if (cont.audit_chain != fresh.audit_chain) {
            fail("continued audit_chain drift seed=" + std::to_string(seed));
        }
    }
    ok("continue_fresh_parity_with_journal");
}

void gate_journal_eight_hop_phase_ladder() {
    rebuild_agent_binary();
    const int seed = 47;
    const int workers = 6;
    const std::string root = "/tmp/verifier_j8";
    const std::string journal = root + "/ladder.journal";
    std::filesystem::create_directories(root);
    reset_journal(journal);

    std::string prev_cp;
    std::string baseline_report;
    std::string baseline_audit;
    for (int hop = 0; hop < 8; ++hop) {
        const std::string out = root + "/hop" + std::to_string(hop);
        const std::string next_cp = root + "/cp" + std::to_string(hop) + ".cp";
        const std::string mode = hop == 0 ? "fresh" : "continued";
        const std::string save = hop < 7 ? next_cp : "";
        const std::string load = hop == 0 ? "" : prev_cp;
        if (run_tb_iter(out, workers, seed, mode, save, load, "", journal) != 0) {
            fail("journal eight hop failed at hop=" + std::to_string(hop));
        }
        const auto got = read_run_outputs(out, seed, workers, mode, hop);
        assert_full_contract(seed, got, workers, mode, hop);
        if (got.phase_id != hop) {
            fail("eight hop phase_id mismatch at hop=" + std::to_string(hop));
        }
        if (baseline_report.empty()) {
            baseline_report = got.report_blob;
            baseline_audit = got.audit_chain;
        } else {
            if (got.report_blob != baseline_report) {
                fail("eight hop report drift at hop=" + std::to_string(hop));
            }
            if (got.audit_chain != baseline_audit) {
                fail("eight hop audit drift at hop=" + std::to_string(hop));
            }
        }
        prev_cp = next_cp;
    }
    ok("journal_eight_hop_phase_ladder");
}

void gate_journal_five_hop_phase_ladder() {
    rebuild_agent_binary();
    const int seed = 47;
    const int workers = 6;
    const std::string root = "/tmp/verifier_j5";
    const std::string journal = root + "/ladder.journal";
    std::filesystem::create_directories(root);
    reset_journal(journal);

    std::string prev_cp;
    std::string baseline_report;
    std::string baseline_audit;
    for (int hop = 0; hop < 5; ++hop) {
        const std::string out = root + "/hop" + std::to_string(hop);
        const std::string next_cp = root + "/cp" + std::to_string(hop) + ".cp";
        const std::string mode = hop == 0 ? "fresh" : "continued";
        const std::string save = hop < 4 ? next_cp : "";
        const std::string load = hop == 0 ? "" : prev_cp;
        if (run_tb_iter(out, workers, seed, mode, save, load, "", journal) != 0) {
            fail("journal five hop failed at hop=" + std::to_string(hop));
        }
        const auto got = read_run_outputs(out, seed, workers, mode, hop);
        assert_full_contract(seed, got, workers, mode, hop);
        if (baseline_report.empty()) {
            baseline_report = got.report_blob;
            baseline_audit = got.audit_chain;
        } else {
            if (got.report_blob != baseline_report) {
                fail("five hop report drift at hop=" + std::to_string(hop));
            }
            if (got.audit_chain != baseline_audit) {
                fail("five hop audit drift at hop=" + std::to_string(hop));
            }
        }
        prev_cp = next_cp;
    }
    ok("journal_five_hop_phase_ladder");
}

void gate_journal_mid_chain_worker_mismatch_rejects() {
    rebuild_agent_binary();
    const std::string root = "/tmp/verifier_jwm";
    const std::string journal = root + "/chain.journal";
    const std::string cp1 = root + "/a.cp";
    const std::string cp2 = root + "/b.cp";
    std::filesystem::create_directories(root);
    reset_journal(journal);
    if (run_tb_iter(root + "/fresh", 4, 53, "fresh", cp1, "", "", journal) != 0) {
        fail("worker mismatch setup fresh failed");
    }
    if (run_tb_iter(root + "/cont1", 4, 53, "continued", cp2, cp1, "", journal) != 0) {
        fail("worker mismatch setup cont1 failed");
    }
    if (run_tb_iter(root + "/bad", 5, 53, "continued", "", cp2, "", journal) == 0) {
        fail("expected journal worker mismatch rejection");
    }
    ok("journal_mid_chain_worker_mismatch_rejects");
}

void gate_journal_corrupt_tail_rejects_continue() {
    rebuild_agent_binary();
    const std::string root = "/tmp/verifier_jcorrupt";
    const std::string journal = root + "/bad.journal";
    const std::string cp = root + "/seed.cp";
    std::filesystem::create_directories(root);
    reset_journal(journal);
    if (run_tb_iter(root + "/setup", 2, 37, "fresh", cp, "", "", journal) != 0) {
        fail("journal corrupt setup failed");
    }
    {
        std::ofstream out(journal, std::ios::app);
        out << "999 999 0 0.0 bad|0.0|6 0\n";
    }
    if (run_tb_iter(root + "/bad", 2, 37, "continued", "", cp, "", journal) == 0) {
        fail("expected corrupt journal tail rejection");
    }
    ok("journal_corrupt_tail_rejects_continue");
}

void gate_journal_invalid_tail_fields_rejects() {
    rebuild_agent_binary();
    const std::string root = "/tmp/verifier_jbadtail";
    const std::string journal = root + "/badtail.journal";
    const std::string cp = root + "/mid.cp";
    std::filesystem::create_directories(root);
    reset_journal(journal);
    if (run_tb_iter(root + "/fresh", 3, 61, "fresh", cp, "", "", journal) != 0) {
        fail("invalid tail setup failed");
    }
    {
        std::ofstream out(journal, std::ios::trunc);
        out << "# tb_iter journal v1\n";
        out << "61 3 incomplete\n";
    }
    if (run_tb_iter(root + "/bad", 3, 61, "continued", "", cp, "", journal) == 0) {
        fail("expected invalid journal tail rejection");
    }
    ok("journal_invalid_tail_fields_rejects");
}

void gate_journal_seed_tail_mismatch_rejects() {
    rebuild_agent_binary();
    const std::string root = "/tmp/verifier_jseed";
    const std::string journal = root + "/seed.journal";
    const std::string cp = root + "/mid.cp";
    std::filesystem::create_directories(root);
    reset_journal(journal);
    if (run_tb_iter(root + "/fresh", 4, 37, "fresh", cp, "", "", journal) != 0) {
        fail("seed mismatch setup failed");
    }
    if (run_tb_iter(root + "/bad", 4, 38, "continued", "", cp, "", journal) == 0) {
        fail("expected journal seed mismatch rejection");
    }
    ok("journal_seed_tail_mismatch_rejects");
}

void gate_phase_id_monotonic_quad_continue() {
    rebuild_agent_binary();
    const int seed = 61;
    const int workers = 5;
    const std::string root = "/tmp/verifier_phase4";
    const std::string journal = root + "/phase.journal";
    std::filesystem::create_directories(root);
    reset_journal(journal);

    std::string prev_cp;
    for (int hop = 0; hop < 4; ++hop) {
        const std::string out = root + "/h" + std::to_string(hop);
        const std::string next_cp = root + "/cp" + std::to_string(hop) + ".cp";
        const std::string mode = hop == 0 ? "fresh" : "continued";
        const std::string save = hop < 3 ? next_cp : "";
        const std::string load = hop == 0 ? "" : prev_cp;
        if (run_tb_iter(out, workers, seed, mode, save, load, "", journal) != 0) {
            fail("quad continue failed at hop=" + std::to_string(hop));
        }
        const auto got = read_run_outputs(out, seed, workers, mode, hop);
        if (got.phase_id != hop) {
            fail("quad continue phase_id mismatch at hop=" + std::to_string(hop));
        }
        prev_cp = next_cp;
    }
    const auto fresh = read_run_outputs(root + "/h0", seed, workers, "fresh", 0);
    const auto last = read_run_outputs(root + "/h3", seed, workers, "continued", 3);
    if (last.report_blob != fresh.report_blob) {
        fail("quad continue changed report relative to fresh");
    }
    ok("phase_id_monotonic_quad_continue");
}

void gate_checkpoint_precision_roundtrip() {
    rebuild_agent_binary();
    const std::vector<std::pair<int, int>> grid = {
        {17, 2}, {27, 3}, {37, 4}, {43, 5}, {47, 6}, {53, 7}, {59, 8}, {67, 9}, {71, 10}};
    const std::string root = "/tmp/verifier_cp_prec";
    for (const auto [seed, workers] : grid) {
        const std::string save = root + "/cp_" + std::to_string(seed) + "_" + std::to_string(workers) + ".cp";
        const std::string out = root + "/run_" + std::to_string(seed);
        if (run_tb_iter(out, workers, seed, "fresh", save, "", "", "") != 0) {
            fail("checkpoint precision run failed");
        }
        const auto meta = read_run_outputs(out, seed, workers, "fresh", 0);
        const auto lines = split_lines(trim(read_text_file(save)));
        if (lines.size() != 3) {
            fail("checkpoint must have three lines");
        }
        if (std::stoi(lines[0]) != seed || std::stoi(lines[1]) != workers) {
            fail("checkpoint header mismatch");
        }
        if (std::abs(std::stod(lines[2]) - meta.dispersion_score) > 1e-9) {
            fail("checkpoint dispersion mismatch");
        }
        if (lines[2].find('.') == std::string::npos || lines[2].size() < 12) {
            fail("checkpoint saved_dispersion lacks full double precision");
        }
    }
    ok("checkpoint_precision_roundtrip");
}

void gate_worker_sweep_audit_invariant_with_journal() {
    rebuild_agent_binary();
    const int seed = 59;
    const std::string root = "/tmp/verifier_jsweep";
    std::string baseline_chain;
    for (int workers = 2; workers <= 10; ++workers) {
        const std::string journal = root + "/w" + std::to_string(workers) + ".journal";
        const std::string cp = root + "/w" + std::to_string(workers) + ".cp";
        std::filesystem::create_directories(root);
        reset_journal(journal);
        if (run_tb_iter(root + "/f_" + std::to_string(workers), workers, seed, "fresh", cp, "", "", journal) !=
            0) {
            fail("journal worker sweep fresh failed");
        }
        if (run_tb_iter(root + "/c_" + std::to_string(workers), workers, seed, "continued", "", cp, "", journal) !=
            0) {
            fail("journal worker sweep continue failed");
        }
        const auto cont = read_run_outputs(root + "/c_" + std::to_string(workers), seed, workers, "continued", 1);
        assert_full_contract(seed, cont, workers, "continued", 1);
        if (baseline_chain.empty()) {
            baseline_chain = cont.audit_chain;
        } else if (cont.audit_chain != baseline_chain) {
            fail("audit_chain worker drift at workers=" + std::to_string(workers));
        }
    }
    ok("worker_sweep_audit_invariant_with_journal");
}

void gate_save_continue_triple_hop_fold_lock() {
    rebuild_agent_binary();
    const std::vector<std::pair<int, int>> grid = {
        {17, 3}, {27, 5}, {47, 7}, {53, 9}, {59, 6}, {61, 8}, {71, 10}, {83, 4}, {97, 6}};
    const std::string root = "/tmp/verifier_triple_hop";
    for (const auto [seed, workers] : grid) {
        const std::string case_root = root + "/" + std::to_string(seed) + "_" + std::to_string(workers);
        const std::string journal = case_root + "/chain.journal";
        const std::string expected = expected_fold_token(seed);
        std::filesystem::create_directories(case_root);
        reset_journal(journal);

        std::string prev_cp;
        for (int hop = 0; hop < 3; ++hop) {
            const std::string out = case_root + "/hop" + std::to_string(hop);
            const std::string next_cp = case_root + "/cp" + std::to_string(hop) + ".cp";
            const std::string mode = hop == 0 ? "fresh" : "continued";
            const std::string save = hop < 2 ? next_cp : "";
            const std::string load = hop == 0 ? "" : prev_cp;
            if (run_tb_iter(out, workers, seed, mode, save, load, "", journal) != 0) {
                fail("triple hop fold lock failed");
            }
            const auto got = read_run_outputs(out, seed, workers, mode, hop);
            if (got.fold_token != expected) {
                fail("triple hop fold_token drift");
            }
            prev_cp = next_cp;
        }
        if (run_tb_iter(case_root + "/direct", workers, seed, "fresh", "", "", "", "") != 0) {
            fail("triple hop direct fresh failed");
        }
        const auto direct = read_run_outputs(case_root + "/direct", seed, workers, "fresh", 0);
        const auto last = read_run_outputs(case_root + "/hop2", seed, workers, "continued", 2);
        if (last.report_blob != direct.report_blob || last.audit_chain != direct.audit_chain) {
            fail("triple hop report drift");
        }
    }
    ok("save_continue_triple_hop_fold_lock");
}

void gate_save_continue_fold_token_lock_journal_chain() {
    rebuild_agent_binary();
    const std::vector<std::pair<int, int>> grid = {
        {17, 3}, {27, 5}, {47, 7}, {53, 9}, {59, 6}, {61, 8}, {71, 10}};
    const std::string root = "/tmp/verifier_fold_chain";
    for (const auto [seed, workers] : grid) {
        const std::string case_root = root + "/" + std::to_string(seed) + "_" + std::to_string(workers);
        const std::string journal = case_root + "/chain.journal";
        const std::string save = case_root + "/mid.cp";
        const std::string expected = expected_fold_token(seed);
        std::filesystem::create_directories(case_root);
        reset_journal(journal);
        if (run_tb_iter(case_root + "/prefix", workers, seed, "fresh", save, "", "", journal) != 0) {
            fail("fold lock journal fresh failed");
        }
        if (run_tb_iter(case_root + "/cont", workers, seed, "continued", "", save, "", journal) != 0) {
            fail("fold lock journal continue failed");
        }
        const auto cont_out = read_run_outputs(case_root + "/cont", seed, workers, "continued", 1);
        if (run_tb_iter(case_root + "/direct", workers, seed, "fresh", "", "", "", "") != 0) {
            fail("fold lock journal direct failed");
        }
        const auto direct_out = read_run_outputs(case_root + "/direct", seed, workers, "fresh", 0);
        if (cont_out.fold_token != direct_out.fold_token || cont_out.fold_token != expected) {
            fail("fold lock journal chain failed");
        }
        if (cont_out.report_blob != direct_out.report_blob) {
            fail("fold lock journal report drift");
        }
    }
    ok("save_continue_fold_token_lock_journal_chain");
}

void gate_layout_dual_flag_invariance() {
    rebuild_agent_binary();
    const std::vector<std::pair<int, int>> grid = {{17, 3}, {27, 7}, {47, 9}, {71, 5}};
    const std::string root = "/tmp/verifier_layout";
    for (const auto [seed, workers] : grid) {
        const std::string plain = root + "/plain_" + std::to_string(seed);
        const std::string layout_a = root + "/layout_a_" + std::to_string(seed);
        const std::string layout_b = root + "/layout_b_" + std::to_string(seed);
        if (run_tb_iter(plain, workers, seed, "fresh", "", "", "", "") != 0) {
            fail("layout plain run failed");
        }
        if (run_tb_iter(layout_a, workers, seed, "fresh", "", "", "/app/data/layout_a.txt", "") != 0) {
            fail("layout_a run failed");
        }
        if (run_tb_iter(layout_b, workers, seed, "fresh", "", "", "/app/data/layout_b.txt", "") != 0) {
            fail("layout_b run failed");
        }
        const auto plain_out = read_run_outputs(plain, seed, workers, "fresh", 0);
        const auto a_out = read_run_outputs(layout_a, seed, workers, "fresh", 0);
        const auto b_out = read_run_outputs(layout_b, seed, workers, "fresh", 0);
        if (plain_out.report_blob != a_out.report_blob || plain_out.report_blob != b_out.report_blob) {
            fail("layout flag changed numeric contract seed=" + std::to_string(seed));
        }
        if (plain_out.fold_token != a_out.fold_token || plain_out.fold_token != b_out.fold_token) {
            fail("layout flag changed fold_token seed=" + std::to_string(seed));
        }
    }
    ok("layout_dual_flag_invariance");
}

void gate_runtime_validation_matrix() {
    rebuild_agent_binary();
    const std::string save = "/tmp/verifier_reject/cp";
    std::filesystem::create_directories("/tmp/verifier_reject");
    if (run_tb_iter("/tmp/verifier_reject/mk", 2, 37, "fresh", save, "", "", "") != 0) {
        fail("validation matrix setup failed");
    }
    if (run_tb_iter("/tmp/verifier_reject/bad_workers", 4, 37, "continued", "", save, "", "") == 0) {
        fail("expected worker mismatch rejection");
    }
    if (run_tb_iter("/tmp/verifier_reject/bad_seed", 2, 38, "continued", "", save, "", "") == 0) {
        fail("expected seed mismatch rejection");
    }
    if (run_tb_iter("/tmp/verifier_reject/noload", 2, 11, "continued", "", "", "", "") == 0) {
        fail("expected continued-without-load rejection");
    }
    if (run_tb_iter("/tmp/verifier_reject/w1", 1, 7, "fresh", "", "", "", "") == 0) {
        fail("expected workers<2 rejection");
    }
    const std::string journal = "/tmp/verifier_reject/nojournal.journal";
    reset_journal(journal);
    if (run_tb_iter("/tmp/verifier_reject/nojournal", 2, 37, "continued", "", save, "", journal) == 0) {
        fail("expected continued-without-journal-history rejection");
    }
    ok("runtime_validation_matrix");
}

void gate_continued_report_neutral_parity() {
    rebuild_agent_binary();
    const std::string root = "/tmp/verifier_neutral";
    for (int si = 0; si < kContinueSeedCount; ++si) {
        const int seed = kContinueSeeds[si];
        const int workers = 5;
        const std::string journal = root + "/j_" + std::to_string(seed) + ".journal";
        const std::string cp = root + "/cp_" + std::to_string(seed) + ".cp";
        const std::string fresh_out = root + "/fresh_" + std::to_string(seed);
        const std::string cont_out = root + "/cont_" + std::to_string(seed);
        std::filesystem::create_directories(root);
        reset_journal(journal);
        if (run_tb_iter(fresh_out, workers, seed, "fresh", cp, "", "", journal) != 0) {
            fail("neutral parity fresh failed");
        }
        if (run_tb_iter(cont_out, workers, seed, "continued", "", cp, "", journal) != 0) {
            fail("neutral parity continue failed");
        }
        const auto fresh = read_run_outputs(fresh_out, seed, workers, "fresh", 0);
        const auto cont = read_run_outputs(cont_out, seed, workers, "continued", 1);
        assert_full_contract(seed, cont, workers, "continued", 1);
        if (cont.report_blob != fresh.report_blob) {
            fail("continued weight adjustment changed report seed=" + std::to_string(seed));
        }
        if (cont.objective != fresh.objective) {
            fail("continued objective drift seed=" + std::to_string(seed));
        }
    }
    ok("continued_report_neutral_parity");
}

void gate_continued_epoch_bump_requires_global_spread() {
    rebuild_agent_binary();
    const int seed = 71;
    const int workers = 4;
    const std::string root = "/tmp/verifier_epoch_bump";
    const std::string journal = root + "/bump.journal";
    const std::string cp = root + "/mid.cp";
    std::filesystem::create_directories(root);
    reset_journal(journal);
    if (run_tb_iter(root + "/fresh", workers, seed, "fresh", cp, "", "", journal) != 0) {
        fail("epoch bump fresh failed");
    }
    if (run_tb_iter(root + "/cont", workers, seed, "continued", "", cp, "", journal) != 0) {
        fail("epoch bump continue failed");
    }
    const auto fresh = read_run_outputs(root + "/fresh", seed, workers, "fresh", 0);
    const auto cont = read_run_outputs(root + "/cont", seed, workers, "continued", 1);
    assert_full_contract(seed, cont, workers, "continued", 1);
    if (cont.report_blob != fresh.report_blob) {
        fail("continued epoch bump altered report relative to fresh");
    }
    ok("continued_epoch_bump_requires_global_spread");
}

void gate_dispersion_objective_formula_grid() {
    rebuild_agent_binary();
    const std::string root = "/tmp/verifier_disp_obj";
    for (int si = 0; si < kDispersionFormulaSeedCount; ++si) {
        const int seed = kDispersionFormulaSeeds[si];
        const std::string out = root + "/s" + std::to_string(seed);
        if (run_tb_iter(out, 2, seed, "fresh", "", "", "", "") != 0) {
            fail("dispersion objective run failed");
        }
        const auto got = read_run_outputs(out, seed, 2, "fresh", 0);
        const auto exp = expected_report(seed);
        const double expected_disp = expected_dispersion(seed);
        if (std::abs(got.dispersion_score - expected_disp) > 1e-9) {
            fail("dispersion_score formula mismatch seed=" + std::to_string(seed));
        }
        if (std::abs(got.objective - exp.objective) > 1e-9) {
            fail("objective formula mismatch seed=" + std::to_string(seed));
        }
    }
    ok("dispersion_objective_formula_grid");
}

void gate_dispersion_stream_formula_seeds() {
    rebuild_agent_binary();
    const std::string root = "/tmp/verifier_disp_formula";
    for (int si = 0; si < kDispersionFormulaSeedCount; ++si) {
        const int seed = kDispersionFormulaSeeds[si];
        const std::string out = root + "/s" + std::to_string(seed);
        if (run_tb_iter(out, 2, seed, "fresh", "", "", "", "") != 0) {
            fail("dispersion formula run failed");
        }
        const auto got = read_run_outputs(out, seed, 2, "fresh", 0);
        const double expected = expected_dispersion(seed);
        if (std::abs(got.dispersion_score - expected) > 1e-9) {
            fail("dispersion_score formula mismatch seed=" + std::to_string(seed));
        }
    }
    ok("dispersion_stream_formula_seeds");
}

using GateFn = void (*)();

const std::vector<std::pair<std::string, GateFn>> kGates = {
    {"rebuild_agent_binary", gate_rebuild_agent_binary},
    {"cases_csv_immutable", gate_cases_csv_immutable},
    {"worker_antipode_blob_lock", gate_worker_antipode_blob_lock},
    {"parallel_full_contract_worker_sweep", gate_parallel_full_contract_worker_sweep},
    {"fold_token_exact_precision_sweep", gate_fold_token_exact_precision_sweep},
    {"weight_pre_renorm_precision_seeds", gate_weight_pre_renorm_precision_seeds},
    {"objective_cross_worker_invariance", gate_objective_cross_worker_invariance},
    {"audit_chain_antipode_lock", gate_audit_chain_antipode_lock},
    {"continue_fresh_parity_with_journal", gate_continue_fresh_parity_with_journal},
    {"journal_eight_hop_phase_ladder", gate_journal_eight_hop_phase_ladder},
    {"journal_mid_chain_worker_mismatch_rejects", gate_journal_mid_chain_worker_mismatch_rejects},
    {"journal_corrupt_tail_rejects_continue", gate_journal_corrupt_tail_rejects_continue},
    {"journal_invalid_tail_fields_rejects", gate_journal_invalid_tail_fields_rejects},
    {"journal_seed_tail_mismatch_rejects", gate_journal_seed_tail_mismatch_rejects},
    {"checkpoint_precision_roundtrip", gate_checkpoint_precision_roundtrip},
    {"save_continue_triple_hop_fold_lock", gate_save_continue_triple_hop_fold_lock},
    {"worker_sweep_audit_invariant_with_journal", gate_worker_sweep_audit_invariant_with_journal},
    {"layout_dual_flag_invariance", gate_layout_dual_flag_invariance},
    {"runtime_validation_matrix", gate_runtime_validation_matrix},
    {"continued_report_neutral_parity", gate_continued_report_neutral_parity},
    {"dispersion_objective_formula_grid", gate_dispersion_objective_formula_grid},
};

}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        fail("usage: tb_iter_verifier <gate-name>|all");
    }
    const std::string target = argv[1];
    std::vector<std::string> names;
    if (target == "all") {
        for (const auto& gate : kGates) {
            names.push_back(gate.first);
        }
    } else {
        names.push_back(target);
    }

    for (const auto& name : names) {
        bool found = false;
        for (const auto& gate : kGates) {
            if (gate.first == name) {
                gate.second();
                found = true;
                break;
            }
        }
        if (!found) {
            fail("unknown gate: " + name);
        }
    }
    return 0;
}
