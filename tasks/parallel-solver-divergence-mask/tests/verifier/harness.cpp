#include "harness.hpp"

#include <array>
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <numeric>
#include <regex>
#include <sstream>
#include <stdexcept>

namespace {

[[noreturn]] void die(const std::string& msg) {
    throw std::runtime_error(msg);
}

int run_cmd(const std::string& cmd) {
    return std::system(cmd.c_str());
}

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

double parse_json_number(const std::string& text, const std::string& key) {
    const std::regex re("\"" + key + "\"\\s*:\\s*(-?[0-9]+(?:\\.[0-9]+(?:[eE][+-]?[0-9]+)?)?)");
    std::smatch m;
    if (!std::regex_search(text, m, re)) {
        die("missing numeric field " + key);
    }
    return std::stod(m[1].str());
}

std::string parse_json_string(const std::string& text, const std::string& key) {
    const std::regex re("\"" + key + "\"\\s*:\\s*\"([^\"]*)\"");
    std::smatch m;
    if (!std::regex_search(text, m, re)) {
        die("missing string field " + key);
    }
    return m[1].str();
}

int parse_json_int(const std::string& text, const std::string& key) {
    return static_cast<int>(parse_json_number(text, key));
}

std::vector<std::pair<std::string, double>> parse_assets(const std::string& text) {
    std::vector<std::pair<std::string, double>> out;
    const std::regex row_re("\\{\\s*\"id\"\\s*:\\s*\"([^\"]+)\"\\s*,\\s*\"weight\"\\s*:\\s*(-?[0-9]+(?:\\.[0-9]+(?:[eE][+-]?[0-9]+)?)?)\\s*\\}");
    auto begin = std::sregex_iterator(text.begin(), text.end(), row_re);
    auto end = std::sregex_iterator();
    for (auto it = begin; it != end; ++it) {
        out.emplace_back((*it)[1].str(), std::stod((*it)[2].str()));
    }
    if (out.empty()) {
        die("no assets parsed from report.json");
    }
    return out;
}

std::string canonical_report_blob(const std::string& report_path) {
    const auto assets = parse_assets(read_text_file(report_path));
    const double objective = parse_json_number(read_text_file(report_path), "objective");
    std::ostringstream os;
    os << "{\"assets\":[";
    for (size_t i = 0; i < assets.size(); ++i) {
        if (i) {
            os << ',';
        }
        os << "{\"id\":\"" << assets[i].first << "\",\"weight\":" << std::setprecision(17) << assets[i].second
           << '}';
    }
    os << "],\"objective\":" << std::setprecision(17) << objective << '}';
    return os.str();
}

}  // namespace

void rebuild_agent_binary() {
    std::filesystem::remove_all("/app/build");
    if (run_cmd(
            "cmake -S /app/environment -B /app/build -DCMAKE_BUILD_TYPE=Release >/tmp/verifier_cmake.log 2>&1") != 0) {
        die("cmake configure failed for /app/environment");
    }
    if (run_cmd("cmake --build /app/build --parallel 1 >/tmp/verifier_build.log 2>&1") != 0) {
        die("cmake build failed for /app/environment");
    }
    if (run_cmd("cp /app/build/tb_iter /usr/local/bin/tb_iter") != 0) {
        die("failed to install rebuilt tb_iter");
    }
    if (!std::filesystem::is_regular_file("/app/build/tb_iter")) {
        die("missing rebuilt /app/build/tb_iter");
    }
}

int run_tb_iter(
    const std::string& out_dir,
    int workers,
    int seed,
    const std::string& mode,
    const std::string& save_path,
    const std::string& load_path,
    const std::string& layout_path,
    const std::string& journal_path) {
    std::filesystem::create_directories(out_dir);
    std::ostringstream cmd;
    cmd << "/usr/local/bin/tb_iter"
        << " --out " << out_dir << " --workers " << workers << " --seed " << seed << " --mode " << mode;
    if (!save_path.empty()) {
        cmd << " --save " << save_path;
    }
    if (!load_path.empty()) {
        cmd << " --load " << load_path;
    }
    if (!layout_path.empty()) {
        cmd << " --layout " << layout_path;
    }
    if (!journal_path.empty()) {
        cmd << " --journal " << journal_path;
    }
    cmd << " >/tmp/tb_iter_stdout.log 2>/tmp/tb_iter_stderr.log";
    return run_cmd(cmd.str());
}

RunOutputs read_run_outputs(
    const std::string& out_dir,
    int seed,
    int workers,
    const std::string& mode,
    int expected_phase_id) {
    const std::string report_path = out_dir + "/report.json";
    const std::string meta_path = out_dir + "/run_meta.json";
    const std::string report_text = read_text_file(report_path);
    const std::string meta_text = read_text_file(meta_path);
    RunOutputs out{};
    out.assets = parse_assets(report_text);
    out.objective = parse_json_number(report_text, "objective");
    out.seed = parse_json_int(meta_text, "seed");
    out.workers = parse_json_int(meta_text, "workers");
    out.mode = parse_json_string(meta_text, "mode");
    out.phase_id = parse_json_int(meta_text, "phase_id");
    out.fold_token = parse_json_string(meta_text, "fold_token");
    out.dispersion_score = parse_json_number(meta_text, "dispersion_score");
    out.audit_chain = parse_json_string(meta_text, "audit_chain");
    out.report_blob = canonical_report_blob(report_path);
    if (out.seed != seed || out.workers != workers || out.mode != mode) {
        die("run_meta.json metadata mismatch for seed=" + std::to_string(seed));
    }
    if (out.phase_id != expected_phase_id) {
        die("run_meta.json phase_id mismatch for seed=" + std::to_string(seed));
    }
    return out;
}

void assert_assets_close(
    const std::vector<std::pair<std::string, double>>& got,
    const std::vector<std::pair<std::string, double>>& exp,
    double tol,
    const std::string& label) {
    if (got.size() != exp.size()) {
        die(label + ": asset count mismatch");
    }
    for (size_t i = 0; i < got.size(); ++i) {
        if (got[i].first != exp[i].first) {
            die(label + ": asset id mismatch at index " + std::to_string(i));
        }
        if (std::abs(got[i].second - exp[i].second) > tol) {
            die(label + ": weight mismatch for " + got[i].first);
        }
    }
}

void assert_full_contract(
    int seed,
    const RunOutputs& got,
    int workers,
    const std::string& mode,
    int phase_id) {
    const auto exp = expected_report(seed);
    assert_assets_close(got.assets, exp.assets, 1e-15, "full_contract assets");
    if (std::abs(got.objective - exp.objective) > 1e-9) {
        die("full_contract objective mismatch");
    }
    if (std::abs(got.dispersion_score - expected_dispersion(seed)) > 1e-9) {
        die("full_contract dispersion mismatch");
    }
    if (got.fold_token != expected_fold_token(seed)) {
        die("full_contract fold_token mismatch");
    }
    if (got.audit_chain != expected_audit_chain(seed)) {
        die("full_contract audit_chain mismatch");
    }
    double wsum = 0.0;
    for (const auto& [id, w] : got.assets) {
        (void)id;
        if (w < 0.0001 - 1e-15) {
            die("full_contract weight below minimum");
        }
        wsum += w;
    }
    if (std::abs(wsum - 1.0) > 1e-9) {
        die("full_contract weights must sum to 1");
    }
    for (size_t i = 1; i < got.assets.size(); ++i) {
        if (got.assets[i - 1].first > got.assets[i].first) {
            die("full_contract assets must be sorted by id");
        }
    }
    if (got.seed != seed || got.workers != workers || got.mode != mode) {
        die("full_contract meta mismatch");
    }
}

std::string read_text_file(const std::string& path) {
    std::ifstream in(path);
    if (!in) {
        die("cannot read " + path);
    }
    std::ostringstream ss;
    ss << in.rdbuf();
    return ss.str();
}

std::string sha256_file(const std::string& path) {
    std::array<char, 256> buf{};
    const std::string cmd = "sha256sum " + path + " 2>/dev/null";
    FILE* fp = popen(cmd.c_str(), "r");
    if (!fp) {
        die("sha256sum failed for " + path);
    }
    if (fgets(buf.data(), static_cast<int>(buf.size()), fp) == nullptr) {
        pclose(fp);
        die("sha256sum produced no output for " + path);
    }
    pclose(fp);
    std::istringstream iss(buf.data());
    std::string digest;
    iss >> digest;
    return digest;
}

void reset_journal(const std::string& path) {
    std::ofstream out(path, std::ios::trunc);
    if (!out) {
        die("cannot reset journal at " + path);
    }
    out << "# tb_iter journal v1\n";
}
