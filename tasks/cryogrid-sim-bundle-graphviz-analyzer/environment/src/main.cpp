#include "cryogrid/dot_emitter.hpp"
#include "cryogrid/metrics_json.hpp"
#include "cryogrid/bundle_spec_loader.hpp"
#include "cryogrid/stability_check.hpp"
#include "cryogrid/stage_graph.hpp"
#include "cryogrid/variance_engine.hpp"

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <string>

namespace fs = std::filesystem;

static void usage() {
    std::cerr << "usage: cryogrid-analyze --spec <path> --out-dir <dir> [--memo-dir <dir>]\n";
}

int main(int argc, char** argv) {
    std::string specPath;
    std::string outDir = "/app/output";
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--spec" && i + 1 < argc) {
            specPath = argv[++i];
        } else if (arg == "--out-dir" && i + 1 < argc) {
            outDir = argv[++i];
        } else if (arg == "--memo-dir" && i + 1 < argc) {
            ++i;
        } else {
            usage();
            return 2;
        }
    }
    if (specPath.empty()) {
        usage();
        return 2;
    }

    try {
        cryogrid::BundleSpecLoader loader;
        cryogrid::BundleSpec bundle = loader.loadFile(specPath);
        cryogrid::StageGraph graph;
        cryogrid::VarianceEngine variance;
        cryogrid::StabilityCheck stability;
        cryogrid::DotEmitter dot;
        cryogrid::MetricsJson metrics;

        auto vars = variance.compute(bundle);
        auto loops = stability.findUnstableLoops(bundle);

        cryogrid::AnalysisResult result;
        result.stage_order = graph.pipelineOrder(bundle);
        for (const auto& id : graph.dependencyOrder(bundle)) {
            result.variances.emplace_back(id, vars.at(id));
        }
        result.unstable_loops = loops;
        result.stable = loops.empty();

        fs::create_directories(outDir);
        std::ofstream dotOut(fs::path(outDir) / "uncertainty-graph.dot");
        dotOut << dot.emit(bundle, result);
        std::ofstream jsonOut(fs::path(outDir) / "metrics-report.json");
        jsonOut << metrics.emit(bundle, result);
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << ex.what() << "\n";
        return 1;
    }
}
