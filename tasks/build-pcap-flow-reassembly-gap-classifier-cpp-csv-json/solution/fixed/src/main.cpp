#include <algorithm>
#include <cctype>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>

struct Row {
    std::string stream_id;
    long long packet_no = 0;
    std::string ts;
    std::string src;
    std::string dst;
    long long seq = 0;
    long long ack = 0;
    long long payload_len = 0;
    std::string flags;
};

struct Diagnostic {
    int row = 0;
    std::string error;
};

struct Gap {
    std::string direction;
    long long start = 0;
    long long end = 0;
    long long introduced_by = 0;
    std::string status = "open";
    long long filled_by = -1;
};

struct Segment {
    long long packet_no = 0;
    std::string direction;
    long long seq = 0;
    long long end_seq = 0;
    long long payload_len = 0;
    std::string flags;
    std::string status;
    long long expected_before = 0;
    bool has_gap = false;
    long long gap_start = 0;
    long long gap_end = 0;
    bool fills_gap = false;
};

static std::string json_escape(const std::string& s) {
    std::string out;
    for (char ch : s) {
        switch (ch) {
            case '\\': out += "\\\\"; break;
            case '"': out += "\\\""; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default: out += ch; break;
        }
    }
    return out;
}

static void write_string(std::ostream& out, const std::string& s) {
    out << '"' << json_escape(s) << '"';
}

static std::vector<std::string> split_csv(const std::string& line) {
    std::vector<std::string> fields;
    std::string field;
    bool quoted = false;
    for (size_t i = 0; i < line.size(); ++i) {
        char ch = line[i];
        if (quoted) {
            if (ch == '"' && i + 1 < line.size() && line[i + 1] == '"') {
                field.push_back('"');
                ++i;
            } else if (ch == '"') {
                quoted = false;
            } else {
                field.push_back(ch);
            }
        } else if (ch == '"') {
            quoted = true;
        } else if (ch == ',') {
            fields.push_back(field);
            field.clear();
        } else {
            field.push_back(ch);
        }
    }
    fields.push_back(field);
    return fields;
}

static bool is_blank_record(const std::vector<std::string>& fields) {
    for (const std::string& field : fields) {
        if (!field.empty()) return false;
    }
    return true;
}

static bool parse_nonnegative(const std::string& text, long long& value) {
    if (text.empty()) return false;
    for (unsigned char ch : text) {
        if (!std::isdigit(ch)) return false;
    }
    try {
        value = std::stoll(text);
    } catch (...) {
        return false;
    }
    return value >= 0;
}

static std::string direction_of(const Row& row) {
    return row.src + " -> " + row.dst;
}

static bool valid_flags(const std::string& flags, long long payload_len) {
    if (flags.empty()) return false;
    std::set<char> seen;
    for (char ch : flags) {
        if (std::string("AFPRS").find(ch) == std::string::npos) return false;
        if (seen.count(ch)) return false;
        seen.insert(ch);
    }
    if (seen.count('R')) {
        if (payload_len != 0) return false;
        return flags == "R" || flags == "AR";
    }
    return true;
}

static long long consumed_len(const Row& row) {
    if (row.flags.find('R') != std::string::npos) return 0;
    long long consumed = row.payload_len;
    if (row.flags.find('S') != std::string::npos) ++consumed;
    if (row.flags.find('F') != std::string::npos) ++consumed;
    return consumed;
}

static bool advance_frontier(long long& expected,
                             const std::vector<std::pair<long long, long long>>& intervals,
                             std::vector<Gap>& gaps,
                             long long packet_no,
                             const std::string& direction) {
    bool changed = true;
    while (changed) {
        changed = false;
        for (const auto& interval : intervals) {
            if (interval.first <= expected && expected < interval.second) {
                expected = interval.second;
                changed = true;
            }
        }
    }
    bool filled = false;
    for (Gap& gap : gaps) {
        if (gap.direction == direction && gap.status == "open" && expected >= gap.end) {
            gap.status = "filled";
            gap.filled_by = packet_no;
            filled = true;
        }
    }
    return filled;
}

struct StreamResult {
    std::string stream_id;
    std::vector<Segment> segments;
    std::vector<Gap> gaps;
    std::map<std::string, long long> counts;
    std::set<std::string> directions;
    long long bytes_observed = 0;
};

struct DirectionState {
    bool initialized = false;
    long long expected = 0;
    std::vector<std::pair<long long, long long>> intervals;
    std::set<std::pair<long long, long long>> seen_gaps;
};

static StreamResult classify_stream(const std::string& stream_id, const std::vector<Row>& rows) {
    StreamResult result;
    result.stream_id = stream_id;
    for (const char* key : {"in_order", "out_of_order", "retransmit", "overlap", "zero_length", "reset"}) {
        result.counts[key] = 0;
    }

    std::map<std::string, DirectionState> states;

    for (const Row& row : rows) {
        const std::string direction = direction_of(row);
        result.directions.insert(direction);
        DirectionState& state = states[direction];
        const long long consumed = consumed_len(row);
        Segment segment;
        segment.packet_no = row.packet_no;
        segment.direction = direction;
        segment.seq = row.seq;
        segment.end_seq = row.seq + consumed;
        segment.payload_len = row.payload_len;
        segment.flags = row.flags;
        result.bytes_observed += row.payload_len;

        if (row.flags.find('R') != std::string::npos) {
            segment.expected_before = state.initialized ? state.expected : row.seq;
            segment.status = "reset";
            for (Gap& gap : result.gaps) {
                if (gap.direction == direction && gap.status == "open") {
                    gap.status = "abandoned";
                }
            }
            state = DirectionState();
        } else if (consumed == 0) {
            segment.expected_before = state.initialized ? state.expected : row.seq;
            segment.status = "zero_length";
        } else {
            if (!state.initialized) {
                state.expected = row.seq;
                state.initialized = true;
            }
            segment.expected_before = state.expected;
            if (segment.end_seq <= state.expected) {
                segment.status = "retransmit";
            } else if (row.seq < state.expected) {
                segment.status = "overlap";
                state.intervals.push_back({row.seq, segment.end_seq});
                segment.fills_gap = advance_frontier(state.expected, state.intervals, result.gaps, row.packet_no, direction);
            } else if (row.seq == state.expected) {
                segment.status = "in_order";
                state.intervals.push_back({row.seq, segment.end_seq});
                segment.fills_gap = advance_frontier(state.expected, state.intervals, result.gaps, row.packet_no, direction);
            } else {
                segment.status = "out_of_order";
                segment.has_gap = true;
                segment.gap_start = state.expected;
                segment.gap_end = row.seq;
                if (!state.seen_gaps.count({state.expected, row.seq})) {
                    result.gaps.push_back({direction, state.expected, row.seq, row.packet_no, "open", -1});
                    state.seen_gaps.insert({state.expected, row.seq});
                }
                state.intervals.push_back({row.seq, segment.end_seq});
            }
        }
        result.counts[segment.status]++;
        result.segments.push_back(segment);
    }
    return result;
}

static void write_summary(std::ostream& out, const StreamResult& stream) {
    out << "\"segments\":" << stream.segments.size()
        << ",\"directions\":" << stream.directions.size()
        << ",\"bytes_observed\":" << stream.bytes_observed
        << ",\"in_order\":" << stream.counts.at("in_order")
        << ",\"out_of_order\":" << stream.counts.at("out_of_order")
        << ",\"retransmit\":" << stream.counts.at("retransmit")
        << ",\"overlap\":" << stream.counts.at("overlap")
        << ",\"zero_length\":" << stream.counts.at("zero_length")
        << ",\"reset\":" << stream.counts.at("reset")
        << ",\"gaps\":" << stream.gaps.size()
        << ",\"open_gaps\":" << std::count_if(stream.gaps.begin(), stream.gaps.end(), [](const Gap& gap) {
            return gap.status == "open";
        })
        << ",\"abandoned_gaps\":" << std::count_if(stream.gaps.begin(), stream.gaps.end(), [](const Gap& gap) {
            return gap.status == "abandoned";
        });
}

int main(int argc, char** argv) {
    std::string csv_path;
    std::string out_path;
    std::string stream_filter;
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--csv" && i + 1 < argc) {
            csv_path = argv[++i];
        } else if (arg == "--out" && i + 1 < argc) {
            out_path = argv[++i];
        } else if (arg == "--stream" && i + 1 < argc) {
            stream_filter = argv[++i];
        } else {
            std::cerr << "usage: flowgap --csv <absolute-path> --out <absolute-path> [--stream <stream_id>]\n";
            return 2;
        }
    }
    if (csv_path.empty() || out_path.empty()) {
        std::cerr << "usage: flowgap --csv <absolute-path> --out <absolute-path> [--stream <stream_id>]\n";
        return 2;
    }
    if (csv_path.empty() || csv_path[0] != '/') {
        std::cerr << "csv path must be absolute: " << csv_path << "\n";
        return 2;
    }
    if (out_path.empty() || out_path[0] != '/') {
        std::cerr << "out path must be absolute: " << out_path << "\n";
        return 2;
    }

    std::ifstream input(csv_path);
    if (!input) {
        std::cerr << "cannot open csv: " << csv_path << "\n";
        return 1;
    }

    const std::vector<std::string> expected_header = {
        "stream_id", "packet_no", "ts", "src", "dst", "seq", "ack", "payload_len", "flags"
    };
    std::string line;
    int file_row = 0;
    bool found_header = false;
    while (std::getline(input, line)) {
        ++file_row;
        if (!line.empty() && line.back() == '\r') line.pop_back();
        std::vector<std::string> header = split_csv(line);
        if (is_blank_record(header)) continue;
        if (header != expected_header) {
            std::cerr << "invalid csv header\n";
            return 1;
        }
        found_header = true;
        break;
    }
    if (!found_header) {
        std::cerr << "empty csv\n";
        return 1;
    }

    std::map<std::string, std::vector<Row>> grouped;
    std::vector<Diagnostic> diagnostics;
    std::set<std::string> seen_packets;
    std::map<std::string, std::string> last_ts;
    int rows_read = 0;
    int rows_skipped = 0;
    while (std::getline(input, line)) {
        ++file_row;
        if (!line.empty() && line.back() == '\r') line.pop_back();
        std::vector<std::string> fields = split_csv(line);
        if (is_blank_record(fields)) continue;
        ++rows_read;
        if (fields.size() != 9) {
            diagnostics.push_back({file_row, "wrong column count"});
            ++rows_skipped;
            continue;
        }
        if (fields[0].empty()) {
            diagnostics.push_back({file_row, "blank stream_id"});
            ++rows_skipped;
            continue;
        }
        Row row;
        row.stream_id = fields[0];
        row.ts = fields[2];
        row.src = fields[3];
        row.dst = fields[4];
        row.flags = fields[8];
        if (!parse_nonnegative(fields[1], row.packet_no) ||
            !parse_nonnegative(fields[5], row.seq) ||
            !parse_nonnegative(fields[6], row.ack) ||
            !parse_nonnegative(fields[7], row.payload_len)) {
            diagnostics.push_back({file_row, "invalid integer"});
            ++rows_skipped;
            continue;
        }
        if (!valid_flags(row.flags, row.payload_len)) {
            diagnostics.push_back({file_row, "invalid flags"});
            ++rows_skipped;
            continue;
        }
        const std::string direction_key = row.stream_id + "\x1f" + row.src + "\x1f" + row.dst;
        const std::string packet_key = direction_key + "\x1f" + std::to_string(row.packet_no);
        if (seen_packets.count(packet_key)) {
            diagnostics.push_back({file_row, "duplicate packet_no"});
            ++rows_skipped;
            continue;
        }
        const auto last = last_ts.find(direction_key);
        if (last != last_ts.end() && row.ts < last->second) {
            diagnostics.push_back({file_row, "timestamp regression"});
            ++rows_skipped;
            continue;
        }
        seen_packets.insert(packet_key);
        last_ts[direction_key] = row.ts;
        if (stream_filter.empty() || row.stream_id == stream_filter) {
            grouped[row.stream_id].push_back(row);
        }
    }

    std::vector<StreamResult> streams;
    for (const auto& item : grouped) {
        streams.push_back(classify_stream(item.first, item.second));
    }

    long long total_segments = 0;
    long long total_directions = 0;
    long long total_bytes = 0;
    std::map<std::string, long long> total_counts;
    for (const char* key : {"in_order", "out_of_order", "retransmit", "overlap", "zero_length", "reset"}) {
        total_counts[key] = 0;
    }
    long long total_gaps = 0;
    long long total_open_gaps = 0;
    long long total_abandoned_gaps = 0;
    for (const StreamResult& stream : streams) {
        total_segments += static_cast<long long>(stream.segments.size());
        total_directions += static_cast<long long>(stream.directions.size());
        total_bytes += stream.bytes_observed;
        total_gaps += static_cast<long long>(stream.gaps.size());
        total_open_gaps += std::count_if(stream.gaps.begin(), stream.gaps.end(), [](const Gap& gap) {
            return gap.status == "open";
        });
        total_abandoned_gaps += std::count_if(stream.gaps.begin(), stream.gaps.end(), [](const Gap& gap) {
            return gap.status == "abandoned";
        });
        for (const auto& count : stream.counts) {
            total_counts[count.first] += count.second;
        }
    }

    std::ofstream out(out_path);
    out << "{\"input\":{\"csv\":";
    write_string(out, csv_path);
    out << ",\"stream_filter\":";
    if (stream_filter.empty()) out << "null"; else write_string(out, stream_filter);
    out << ",\"rows_read\":" << rows_read << ",\"rows_skipped\":" << rows_skipped << "},\"streams\":[";
    for (size_t i = 0; i < streams.size(); ++i) {
        if (i) out << ",";
        const StreamResult& stream = streams[i];
        out << "{\"stream_id\":";
        write_string(out, stream.stream_id);
        out << ",\"segments\":[";
        for (size_t j = 0; j < stream.segments.size(); ++j) {
            if (j) out << ",";
            const Segment& segment = stream.segments[j];
            out << "{\"packet_no\":" << segment.packet_no
                << ",\"direction\":";
            write_string(out, segment.direction);
            out << ",\"seq\":" << segment.seq
                << ",\"end_seq\":" << segment.end_seq
                << ",\"payload_len\":" << segment.payload_len
                << ",\"flags\":";
            write_string(out, segment.flags);
            out << ",\"status\":";
            write_string(out, segment.status);
            out << ",\"expected_before\":" << segment.expected_before << ",\"gap_before\":";
            if (segment.has_gap) {
                out << "{\"start\":" << segment.gap_start
                    << ",\"end\":" << segment.gap_end
                    << ",\"length\":" << (segment.gap_end - segment.gap_start) << "}";
            } else {
                out << "null";
            }
            out << ",\"fills_gap\":" << (segment.fills_gap ? "true" : "false") << "}";
        }
        out << "],\"gaps\":[";
        for (size_t j = 0; j < stream.gaps.size(); ++j) {
            if (j) out << ",";
            const Gap& gap = stream.gaps[j];
            out << "{\"direction\":";
            write_string(out, gap.direction);
            out << ",\"start\":" << gap.start
                << ",\"end\":" << gap.end
                << ",\"length\":" << (gap.end - gap.start)
                << ",\"introduced_by\":" << gap.introduced_by
                << ",\"status\":";
            write_string(out, gap.status);
            out << ",\"filled_by\":";
            if (gap.filled_by < 0) out << "null"; else out << gap.filled_by;
            out << "}";
        }
        out << "],\"summary\":{";
        write_summary(out, stream);
        out << "}}";
    }
    out << "],\"totals\":{\"streams\":" << streams.size()
        << ",\"segments\":" << total_segments
        << ",\"directions\":" << total_directions
        << ",\"bytes_observed\":" << total_bytes
        << ",\"in_order\":" << total_counts["in_order"]
        << ",\"out_of_order\":" << total_counts["out_of_order"]
        << ",\"retransmit\":" << total_counts["retransmit"]
        << ",\"overlap\":" << total_counts["overlap"]
        << ",\"zero_length\":" << total_counts["zero_length"]
        << ",\"reset\":" << total_counts["reset"]
        << ",\"gaps\":" << total_gaps
        << ",\"open_gaps\":" << total_open_gaps
        << ",\"abandoned_gaps\":" << total_abandoned_gaps
        << "},\"diagnostics\":[";
    for (size_t i = 0; i < diagnostics.size(); ++i) {
        if (i) out << ",";
        out << "{\"row\":" << diagnostics[i].row << ",\"error\":";
        write_string(out, diagnostics[i].error);
        out << "}";
    }
    out << "]}\n";
    return 0;
}
