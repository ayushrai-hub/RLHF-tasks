#include "score/sidecar_exec.hpp"

#include <cstdlib>
#include <fstream>
#include <sstream>

namespace {
bool run_cmd(const std::string& cmd) {
    return std::system(cmd.c_str()) == 0;
}
}  // namespace

bool SidecarExec::launch(const Json::Value& rows, const Policy& policy, Json::Value& features_out) {
    (void)policy;
    const std::string rows_path = "/tmp/score_rows.json";
    const std::string features_path = "/tmp/score_features.json";
    {
        std::ofstream out(rows_path);
        Json::StreamWriterBuilder builder;
        builder["indentation"] = "";
        out << Json::writeString(builder, rows);
    }
    setenv("FEATURE_NULL_MODE", "zero", 1);
    std::ostringstream cmd;
    cmd << "/opt/sidecar-venv/bin/python3 /app/environment/sidecar/feature_pipe/preprocess.py"
        << " --input " << rows_path << " --output " << features_path;
    if (!run_cmd(cmd.str())) {
        return false;
    }
    std::ifstream in(features_path);
    std::stringstream buffer;
    buffer << in.rdbuf();
    Json::CharReaderBuilder reader;
    std::string errs;
    return Json::parseFromStream(reader, buffer, &features_out, &errs);
}
