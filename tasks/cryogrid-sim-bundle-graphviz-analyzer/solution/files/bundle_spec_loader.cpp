#include "cryogrid/bundle_spec_loader.hpp"

#include <fstream>
#include <stdexcept>

namespace cryogrid {

StageClass parseStageClass(const std::string& text) {
    if (text == "SOURCE") return StageClass::SOURCE;
    if (text == "TRANSFER") return StageClass::TRANSFER;
    if (text == "SINK") return StageClass::SINK;
    if (text == "COUPLER") return StageClass::COUPLER;
    if (text == "FEEDBACK") return StageClass::FEEDBACK;
    return StageClass::UNKNOWN;
}

BundleSpec BundleSpecLoader::loadFile(const std::string& path) const {
    std::ifstream in(path);
    if (!in) {
        throw std::runtime_error("cannot open spec: " + path);
    }
    nlohmann::json root;
    in >> root;
    return loadJson(root);
}

BundleSpec BundleSpecLoader::loadJson(const nlohmann::json& root) const {
    BundleSpec bundle;
    bundle.bundle_id = root.value("bundle_id", "");
    bundle.soil_temp = root.value("soil_temp", 0.0);

    const nlohmann::json& pipeline = root.at("pipeline");
    const nlohmann::json& stagesNode = pipeline.at("stages");
    for (const auto& item : stagesNode) {
        StageSpec stage;
        stage.id = item.value("id", "");
        stage.stage_class = parseStageClass(item.value("class", ""));
        if (item.contains("inputs")) {
            for (const auto& dep : item["inputs"]) {
                stage.inputs.push_back(dep.get<std::string>());
            }
        }
        stage.sigma = item.value("sigma", 0.0);
        stage.kappa = item.value("kappa", 0.0);
        stage.epsilon = item.value("epsilon", 0.01);
        stage.coupling_gain = item.value("coupling_gain", 0.5);
        stage.cryo_exception = item.value("cryo_exception", "");
        bundle.stages.push_back(stage);
    }
    return bundle;
}

}  // namespace cryogrid
