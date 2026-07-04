#include <algorithm>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

struct Row {
    std::string stream_id;
    long long packet_no = 0;
    long long seq = 0;
    long long ack = 0;
    long long payload_len = 0;
    std::string flags;
};

static std::vector<std::string> split_csv(const std::string& line) {
    std::vector<std::string> fields;
    std::stringstream ss(line);
    std::string field;
    while (std::getline(ss, field, ',')) {
        fields.push_back(field);
    }
    return fields;
}

static bool parse_int(const std::string& text, long long& value) {
    if (text.empty()) return false;
    for (char ch : text) {
        if (ch < '0' || ch > '9') return false;
    }
    value = std::stoll(text);
    return true;
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
    if (csv_path[0] != '/') {
        std::cerr << "csv path must be absolute: " << csv_path << "\n";
        return 2;
    }
    if (out_path[0] != '/') {
        std::cerr << "out path must be absolute: " << out_path << "\n";
        return 2;
    }

    std::ifstream input(csv_path);
    if (!input) {
        std::cerr << "cannot open csv\n";
        return 1;
    }

    std::string line;
    std::getline(input, line);
    std::map<std::string, std::vector<Row>> streams;
    int rows_read = 0;
    int rows_skipped = 0;
    while (std::getline(input, line)) {
        if (line.empty()) continue;
        ++rows_read;
        auto fields = split_csv(line);
        if (fields.size() != 9) {
            ++rows_skipped;
            continue;
        }
        Row row;
        row.stream_id = fields[0];
        row.flags = fields[8];
        if (row.stream_id.empty() ||
            !parse_int(fields[1], row.packet_no) ||
            !parse_int(fields[5], row.seq) ||
            !parse_int(fields[6], row.ack) ||
            !parse_int(fields[7], row.payload_len)) {
            ++rows_skipped;
            continue;
        }
        if (!stream_filter.empty() && row.stream_id != stream_filter) continue;
        streams[row.stream_id].push_back(row);
    }

    std::ofstream out(out_path);
    out << "{\"input\":{\"csv\":\"" << csv_path << "\",\"stream_filter\":";
    if (stream_filter.empty()) out << "null"; else out << "\"" << stream_filter << "\"";
    out << ",\"rows_read\":" << rows_read << ",\"rows_skipped\":" << rows_skipped << "},";
    out << "\"streams\":[";
    bool first_stream = true;
    int total_segments = 0;
    for (const auto& item : streams) {
        if (!first_stream) out << ",";
        first_stream = false;
        out << "{\"stream_id\":\"" << item.first << "\",\"segments\":[";
        bool first_seg = true;
        long long expected = item.second.empty() ? 0 : item.second.front().seq;
        int in_order = 0;
        for (const Row& row : item.second) {
            long long consumed = row.payload_len;
            long long end_seq = row.seq + consumed;
            std::string status = "in_order";
            if (consumed == 0) {
                status = "zero_length";
            } else if (row.seq < expected) {
                status = "retransmit";
            } else if (row.seq > expected) {
                status = "out_of_order";
            } else {
                expected = end_seq;
                ++in_order;
            }
            if (!first_seg) out << ",";
            first_seg = false;
            out << "{\"packet_no\":" << row.packet_no
                << ",\"seq\":" << row.seq
                << ",\"end_seq\":" << end_seq
                << ",\"payload_len\":" << row.payload_len
                << ",\"flags\":\"" << row.flags
                << "\",\"status\":\"" << status
                << "\",\"expected_before\":" << expected
                << ",\"gap_before\":null,\"fills_gap\":false}";
            ++total_segments;
        }
        out << "],\"gaps\":[],\"summary\":{\"segments\":" << item.second.size()
            << ",\"bytes_observed\":0,\"in_order\":" << in_order
            << ",\"out_of_order\":0,\"retransmit\":0,\"overlap\":0,\"zero_length\":0,\"gaps\":0,\"open_gaps\":0}}";
    }
    out << "],\"totals\":{\"streams\":" << streams.size()
        << ",\"segments\":" << total_segments
        << ",\"bytes_observed\":0,\"in_order\":0,\"out_of_order\":0,\"retransmit\":0,\"overlap\":0,\"zero_length\":0,\"gaps\":0,\"open_gaps\":0},\"diagnostics\":[]}\n";
    return 0;
}
