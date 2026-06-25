#include "engine.hpp"

#include "audit_digest.hpp"
#include "checkpoint.hpp"
#include "epoch_coordinator.hpp"
#include "layout.hpp"
#include "math_utils.hpp"
#include "metric_fabric.hpp"
#include "reduce_bridge.hpp"
#include "run_journal.hpp"
#include "trace_sink.hpp"
#include <algorithm>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <numeric>
#include <stdexcept>
#include <vector>

namespace {
std::vector<std::vector<double>> shard_values(const std::vector<double>& values, int workers) {
    std::vector<std::vector<double>> chunks(static_cast<size_t>(workers));
    for (size_t i = 0; i < values.size(); ++i) {
        const int slot = static_cast<int>(i % static_cast<size_t>(workers));
        chunks[static_cast<size_t>(slot)].push_back(values[i]);
    }
    return chunks;
}

FoldPack local_pack_from_chunk(const std::vector<double>& chunk) {
    FoldPack p{};
    if (chunk.empty()) {
        return p;
    }
    const double sum = std::accumulate(chunk.begin(), chunk.end(), 0.0);
    const double mn = *std::min_element(chunk.begin(), chunk.end());
    const double mx = *std::max_element(chunk.begin(), chunk.end());
    p.g_norm = sum / static_cast<double>(chunk.size());
    p.g_spread = mx - mn;
    p.g_count = static_cast<int>(chunk.size());
    return p;
}

void append_json_double(std::ostream& os, double v) {
    char buf[64];
    std::snprintf(buf, sizeof(buf), "%.17g", v);
    os << buf;
}

}  // namespace

int run_engine(const RunArgs& args, const std::vector<CaseRow>& rows) {
    if (args.workers < 2) {
        throw std::runtime_error("workers must be >= 2");
    }
    if (!args.layout.empty()) {
        (void)layout_span(args.layout);
    }

    JournalTail prior{};
    if (!args.journal_path.empty()) {
        prior = read_journal_tail(args.journal_path);
    }
    if (args.mode == "continued") {
        if (args.load_path.empty()) {
            throw std::runtime_error("continued mode requires --load");
        }
        if (!args.journal_path.empty()) {
            validate_journal_continuation(prior, args.seed, args.workers);
        }
    }

    std::vector<double> values;
    values.reserve(rows.size());
    for (size_t i = 0; i < rows.size(); ++i) {
        const auto& row = rows[i];
        const double mixed = mix_value(args.seed, static_cast<int>(i));
        values.push_back(row.bias + row.slope * mixed);
    }

    const auto chunks = shard_values(values, args.workers);
    std::vector<FoldPack> packs;
    packs.reserve(chunks.size());
    for (const auto& chunk : chunks) {
        packs.push_back(local_pack_from_chunk(chunk));
    }
    FoldPack seed_fold{};
    seed_fold.g_count = static_cast<int>(values.size());
    FoldPack global = op_b(seed_fold, packs, args.workers);

    VecPack u{packs.front().g_norm, packs.front().g_spread, packs.front().g_count};
    VecPack v{packs.back().g_norm, packs.back().g_spread, packs.back().g_count};
    const double score = op_a(u, v, 1);

    TraceRow trace{};
    op_c(global, trace, 1);

    Checkpoint loaded_cp{};
    bool have_cp = false;
    if (args.mode == "continued") {
        loaded_cp = load_checkpoint(args.load_path);
        if (loaded_cp.seed != args.seed) {
            throw std::runtime_error("checkpoint mismatch");
        }
        (void)loaded_cp.workers;
        (void)loaded_cp.saved_dispersion;
        have_cp = true;
    }

    const int phase_id = args.journal_path.empty() ? 0 : resolve_phase_id(args.journal_path, args.mode);

    const double sum = std::accumulate(values.begin(), values.end(), 0.0);
    const double stream_mean = sum / static_cast<double>(values.size());
    std::vector<double> weights(values.size(), 0.0);
    for (size_t i = 0; i < values.size(); ++i) {
        weights[i] = values[i] / sum;
        if (weights[i] < 0.0001) {
            weights[i] = 0.0001;
        }
    }
    double wsum = std::accumulate(weights.begin(), weights.end(), 0.0);
    for (double& w : weights) {
        w /= wsum;
    }
    const double bump = score * 0.01;
    for (double& w : weights) {
        w += bump;
    }
    wsum = std::accumulate(weights.begin(), weights.end(), 0.0);
    for (double& w : weights) {
        w /= wsum;
    }

    if (have_cp) {
        apply_continued_weight_adjustment(
            weights, values, loaded_cp.saved_dispersion, trace.dispersion, args.mode, phase_id);
    }

    std::vector<size_t> order(rows.size());
    for (size_t i = 0; i < rows.size(); ++i) {
        order[i] = i;
    }
    std::sort(order.begin(), order.end(), [&](size_t a, size_t b) { return rows[a].id < rows[b].id; });

    std::filesystem::create_directories(args.out_dir);
    std::ofstream report(args.out_dir + "/report.json");
    std::ofstream meta(args.out_dir + "/run_meta.json");
    if (!report || !meta) {
        throw std::runtime_error("cannot write output files");
    }

    double objective = 0.0;
    for (size_t i = 0; i < rows.size(); ++i) {
        objective += weights[i] * values[i];
    }
    objective -= stream_mean * 0.01;

    report << "{\n  \"assets\": [\n";
    for (size_t i = 0; i < order.size(); ++i) {
        const size_t idx = order[i];
        report << "    {\"id\": \"" << rows[idx].id << "\", \"weight\": ";
        append_json_double(report, weights[idx]);
        report << "}";
        if (i + 1 != order.size()) {
            report << ",";
        }
        report << "\n";
    }
    report << "  ],\n  \"objective\": ";
    append_json_double(report, objective);
    report << "\n}\n";

    char fold_mean[64];
    char fold_spread[64];
    std::snprintf(fold_mean, sizeof(fold_mean), "%.8f", trace.scalar);
    std::snprintf(fold_spread, sizeof(fold_spread), "%.8f", trace.dispersion);
    const std::string fold_token = std::string(fold_mean) + "|" + fold_spread + "|6";
    const uint64_t audit_link = compute_audit_link(args.seed, fold_token, objective);

    meta << "{\n";
    meta << "  \"seed\": " << args.seed << ",\n";
    meta << "  \"workers\": " << args.workers << ",\n";
    meta << "  \"mode\": \"" << args.mode << "\",\n";
    meta << "  \"phase_id\": " << phase_id << ",\n";
    meta << "  \"fold_token\": \"" << fold_token << "\",\n";
    meta << "  \"dispersion_score\": ";
    append_json_double(meta, trace.dispersion);
    meta << ",\n";
    meta << "  \"audit_chain\": \"" << audit_link_hex(audit_link) << "\"\n";
    meta << "}\n";

    if (!args.save_path.empty()) {
        Checkpoint cp{};
        cp.seed = args.seed;
        cp.workers = args.workers;
        cp.saved_dispersion = trace.dispersion;
        save_checkpoint(args.save_path, cp);
    }

    if (!args.journal_path.empty()) {
        append_journal_entry(
            args.journal_path, args.seed, args.workers, phase_id, trace.dispersion, fold_token, audit_link);
    }

    return 0;
}
