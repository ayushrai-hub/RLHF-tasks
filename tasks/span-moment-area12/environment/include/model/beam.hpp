#pragma once

#include <string>
#include <vector>

namespace beam {

enum class SupportType { PIN, ROLLER };

struct Node {
    double x_m = 0.0;
    SupportType support = SupportType::PIN;
    double settlement_mm = 0.0;
};

struct Segment {
    std::string id;
    double x0_m = 0.0;
    double x1_m = 0.0;
    double E_pa = 0.0;
    double I_m4 = 0.0;
    double width_mm = 0.0;
    double depth_mm = 0.0;
};

struct StiffnessRegion {
    std::string segment_id;
    double x0_m = 0.0;
    double x1_m = 0.0;
    double factor = 1.0;
};

struct PointForce {
    double force_n = 0.0;
    double x_m = 0.0;
};

struct PointMoment {
    double moment_nm = 0.0;
    double x_m = 0.0;
};

struct UdlLoad {
    double w_n_per_m = 0.0;
    double x0_m = 0.0;
    double x1_m = 0.0;
};

struct LoadCase {
    std::string name;
    std::vector<PointForce> point_forces;
    std::vector<PointMoment> point_moments;
    std::vector<UdlLoad> udls;
};

struct CombinationTerm {
    std::string case_name;
    double factor = 1.0;
};

struct Combination {
    std::string name;
    std::vector<CombinationTerm> terms;
};

struct SegmentFrame {
    double origin_m = 0.0;
    double length_m = 0.0;
};

struct BeamModel {
    std::string beam_id;
    int revision = 0;
    std::vector<Node> nodes;
    std::vector<Segment> segments;
    std::vector<StiffnessRegion> stiffness;
    std::vector<LoadCase> load_cases;
    std::vector<Combination> combinations;
};

struct StageDirective {
    bool is_amendment = false;
    bool accept = true;
    std::string integrity;
    std::vector<std::string> replace_segments;
    std::vector<std::string> replace_load_cases;
};

struct CommittedState {
    BeamModel model;
    int committed_revision = 0;
    int amendment_generation = 0;
    int accepted_stages = 0;
    int rejected_stages = 0;
};

struct EnvelopeValues {
    double max_moment_nm = 0.0;
    double min_moment_nm = 0.0;
    double max_shear_n = 0.0;
    double min_shear_n = 0.0;
    double max_deflection_mm = 0.0;
    double min_deflection_mm = 0.0;
    double left_reaction_n = 0.0;
    double right_reaction_n = 0.0;
};

struct ReportProvenance {
    int committed_revision = 0;
    int amendment_generation = 0;
    int accepted_stages = 0;
    int rejected_stages = 0;
};

struct EnvelopeReport {
    int schema_version = 2;
    std::string beam_id;
    std::string combination;
    ReportProvenance provenance;
    EnvelopeValues envelope;
    std::string report_digest;
};

}  // namespace beam
