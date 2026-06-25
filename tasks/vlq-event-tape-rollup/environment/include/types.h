#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace vlt {

struct TapeEvent {
    std::uint64_t tag = 0;
    std::int64_t delta = 0;
    std::vector<std::uint8_t> payload;
};

struct TapeDoc {
    std::uint16_t tape_id = 0;
    std::vector<TapeEvent> events;
};

struct AnswerCell {
    std::string op;
    int from = 0;
    int to = 0;
    int at = 0;
    int mask = 0;
    std::int64_t value = 0;
};

struct PanelRun {
    std::string name;
    int event_count = 0;
    int tag_span = 0;
    std::vector<AnswerCell> answers;
    std::string row_digest;
};

struct CampaignDoc {
    int schema_version = 0;
    std::string campaign_id;
    std::vector<PanelRun> panels;
    std::string digest;
};

}  // namespace vlt
