#include "model/amend.hpp"

#include <map>
#include <sstream>

namespace beam::model {

namespace {

Segment parse_replace_segment_line(const std::string& line) {
  Segment seg;
  std::istringstream row(line.substr(16));
  row >> seg.id >> seg.x0_m >> seg.x1_m;
  const auto e_gpa_pos = line.find("E_gpa=");
  if (e_gpa_pos != std::string::npos) {
    seg.E_pa = std::stod(line.substr(e_gpa_pos + 6)) * 1e9;
  }
  const auto width_pos = line.find("section_width_mm=");
  if (width_pos != std::string::npos) {
    seg.width_mm = std::stod(line.substr(width_pos + 17));
  }
  const auto depth_pos = line.find("section_depth_mm=");
  if (depth_pos != std::string::npos) {
    seg.depth_mm = std::stod(line.substr(depth_pos + 17));
  }
  if (seg.width_mm > 0.0 && seg.depth_mm > 0.0) {
    const double b = seg.width_mm / 1000.0;
    const double h = seg.depth_mm / 1000.0;
    seg.I_m4 = b * h * h * h / 12.0;
  }
  return seg;
}

}  // namespace

std::map<std::string, SegmentFrame> committed_segment_frames(const BeamModel& model) {
  std::map<std::string, SegmentFrame> frames;
  for (const auto& seg : model.segments) {
    frames[seg.id] = SegmentFrame{seg.x0_m, seg.x1_m - seg.x0_m};
  }
  return frames;
}

std::map<std::string, SegmentFrame> pending_segment_frames(const BeamModel& model) {
  return committed_segment_frames(model);
}

double normalize_load_x(const std::map<std::string, SegmentFrame>& frames,
                        const std::string& segment_id,
                        double local_x) {
  const auto it = frames.find(segment_id);
  if (it == frames.end()) {
    return local_x;
  }
  return it->second.origin_m + local_x;
}

void apply_amendment(BeamModel& committed,
                     const BeamModel& pending,
                     const StageDirective& directive,
                     const std::map<std::string, SegmentFrame>& superseded_frames) {
  for (const auto& line : directive.replace_segments) {
    Segment seg = parse_replace_segment_line(line);
    bool replaced = false;
    for (auto& existing : committed.segments) {
      if (existing.id == seg.id) {
        existing = seg;
        replaced = true;
        break;
      }
    }
    if (!replaced) {
      committed.segments.push_back(seg);
    }
  }

  const std::map<std::string, SegmentFrame> pending_frames = pending_segment_frames(pending);

  for (const auto& pending_case : pending.load_cases) {
    LoadCase normalized = pending_case;
    for (auto& pf : normalized.point_forces) {
      pf.x_m = normalize_load_x(superseded_frames, "main", pf.x_m);
      (void)pending_frames;
    }
    for (auto& pm : normalized.point_moments) {
      pm.x_m = normalize_load_x(superseded_frames, "main", pm.x_m);
    }
    for (auto& udl : normalized.udls) {
      udl.x0_m = normalize_load_x(superseded_frames, "main", udl.x0_m);
      udl.x1_m = normalize_load_x(superseded_frames, "main", udl.x1_m);
    }

    bool replaced = false;
    for (auto& existing : committed.load_cases) {
      if (existing.name == normalized.name) {
        existing = normalized;
        replaced = true;
        break;
      }
    }
    if (!replaced) {
      committed.load_cases.push_back(normalized);
    }
  }

  if (!pending.combinations.empty()) {
    committed.combinations = pending.combinations;
  }
  committed.revision = pending.revision;
}

}  // namespace beam::model
