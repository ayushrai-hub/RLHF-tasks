#include "model/analysis.hpp"
#include "model/cache.hpp"
#include "model/stage.hpp"

#include "io/diagnostic.hpp"
#include "report/writer.hpp"

#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace beam::report {
void write_report(const EnvelopeReport& report, const std::string& path);
}

int main(int argc, char** argv) {
    std::vector<std::string> stage_paths;
    std::string combination;
    std::string out_path;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--stage" && i + 1 < argc) {
            stage_paths.push_back(argv[++i]);
        } else if (arg == "--combine" && i + 1 < argc) {
            combination = argv[++i];
        } else if (arg == "--out" && i + 1 < argc) {
            out_path = argv[++i];
        } else {
            std::cerr << "usage: beam-envelope --stage <path>... --combine <name> --out <report.json>\n";
            return 2;
        }
    }

    if (stage_paths.empty() || combination.empty() || out_path.empty()) {
        std::cerr << "usage: beam-envelope --stage <path>... --combine <name> --out <report.json>\n";
        return 2;
    }

    try {
        const auto committed = beam::stage::process_journal(stage_paths);
        const beam::Combination* combo = nullptr;
        for (const auto& candidate : committed.model.combinations) {
            if (candidate.name == combination) {
                combo = &candidate;
                break;
            }
        }
        if (combo == nullptr) {
            throw std::runtime_error("unknown combination: " + combination);
        }

        static beam::cache::EnvelopeStore store;
        const std::string cache_key = beam::cache::envelope_cache_key(committed, combination);
        beam::EnvelopeValues envelope;
        if (const auto cached = store.lookup(cache_key)) {
            envelope = *cached;
        } else {
            envelope = beam::analysis::solve_equilibrium(committed.model, *combo);
            const auto piecewise = beam::analysis::assemble_piecewise(committed.model, *combo, envelope);
            envelope.max_moment_nm = piecewise.max_moment_nm;
            envelope.min_moment_nm = piecewise.min_moment_nm;
            envelope.max_shear_n = piecewise.max_shear_n;
            envelope.min_shear_n = piecewise.min_shear_n;
            const auto deflected = beam::analysis::integrate_deflection(committed.model, *combo, envelope);
            envelope.max_deflection_mm = deflected.max_deflection_mm;
            envelope.min_deflection_mm = deflected.min_deflection_mm;
            store.store(cache_key, envelope);
        }

        beam::EnvelopeReport report;
        report.beam_id = committed.model.beam_id;
        report.combination = combination;
        report.provenance.committed_revision = committed.committed_revision;
        report.provenance.amendment_generation = committed.amendment_generation;
        report.provenance.accepted_stages = committed.accepted_stages;
        report.provenance.rejected_stages = committed.rejected_stages;
        report.envelope = envelope;

        beam::report::write_report(report, out_path);
        return 0;
    } catch (const std::exception& ex) {
        if (fs::exists(out_path)) {
            fs::remove(out_path);
        }
        std::cerr << ex.what() << "\n";
        return 1;
    }
}
