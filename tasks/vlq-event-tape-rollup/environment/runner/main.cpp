#include "constants.h"
#include "stage.h"
#include "types.h"
#include <cctype>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

struct QueryRef {
    std::string op;
    int from = 0;
    int to = 0;
    int at = 0;
    int mask = 0;
};

struct PanelRef {
    std::string name;
    std::string bundle;
    std::vector<QueryRef> queries;
};

static std::string json_escape(const std::string &s) {
    std::string out;
    out.push_back('"');
    for (char ch : s) {
        if (ch == '"' || ch == '\\') {
            out.push_back('\\');
        }
        out.push_back(ch);
    }
    out.push_back('"');
    return out;
}

static std::string slurp(const std::string &path) {
    std::ifstream in(path);
    std::ostringstream os;
    os << in.rdbuf();
    return os.str();
}

static std::string extract_string(const std::string &blob, const std::string &key, size_t start = 0) {
    const std::string needle = '"' + key + '"';
    size_t pos = blob.find(needle, start);
    if (pos == std::string::npos) {
        return "";
    }
    pos = blob.find('"', pos + needle.size());
    if (pos == std::string::npos) {
        return "";
    }
    size_t end = blob.find('"', pos + 1);
    return blob.substr(pos + 1, end - pos - 1);
}

static int extract_int(const std::string &blob, const std::string &key, size_t start = 0) {
    const std::string needle = '"' + key + '"';
    size_t pos = blob.find(needle, start);
    if (pos == std::string::npos) {
        return 0;
    }
    pos = blob.find(':', pos);
    while (pos < blob.size() && (blob[pos] == ':' || std::isspace(static_cast<unsigned char>(blob[pos])))) {
        ++pos;
    }
    return std::atoi(blob.c_str() + pos);
}

static std::vector<PanelRef> load_panels(const std::string &blob) {
    std::vector<PanelRef> out;
    size_t cursor = 0;
    while (true) {
        size_t name_pos = blob.find("\"name\"", cursor);
        if (name_pos == std::string::npos) {
            break;
        }
        size_t next_name = blob.find("\"name\"", name_pos + 6);
        size_t block_end = next_name == std::string::npos ? blob.size() : next_name;
        const std::string block = blob.substr(name_pos, block_end - name_pos);
        PanelRef ref;
        ref.name = extract_string(block, "name");
        ref.bundle = extract_string(block, "bundle");
        size_t qcursor = 0;
        while (true) {
            size_t op_pos = block.find("\"op\"", qcursor);
            if (op_pos == std::string::npos) {
                break;
            }
            QueryRef q;
            q.op = extract_string(block.substr(op_pos), "op");
            if (q.op == "fold") {
                q.from = extract_int(block, "from", op_pos);
                q.to = extract_int(block, "to", op_pos);
            } else if (q.op == "peek") {
                q.at = extract_int(block, "at", op_pos);
            } else if (q.op == "tally") {
                q.mask = extract_int(block, "mask", op_pos);
            }
            ref.queries.push_back(q);
            qcursor = op_pos + 4;
        }
        if (!ref.name.empty() && !ref.bundle.empty()) {
            out.push_back(std::move(ref));
        }
        cursor = block_end;
    }
    return out;
}

int main(int argc, char **argv) {
    if (argc < 3) {
        return 2;
    }
    bool warm = false;
    bool reset = false;
    for (int i = 3; i < argc; ++i) {
        const std::string flag = argv[i];
        if (flag == "--warm") {
            warm = true;
        } else if (flag == "--reset") {
            reset = true;
        }
    }
    if (reset || !warm) {
        vlt::stage::reset_journal();
        vlt::stage::reset_lanes();
    }
    const std::string blob = slurp(argv[1]);
    const std::string out_path = argv[2];
    vlt::CampaignDoc doc;
    doc.schema_version = extract_int(blob, "schema_version");
    doc.campaign_id = extract_string(blob, "campaign_id");
    const std::vector<PanelRef> refs = load_panels(blob);
    const std::string base = "/app/environment/fixtures/";
    std::vector<std::string> panel_order;
    for (const PanelRef &ref : refs) {
        panel_order.push_back(ref.name);
        vlt::PanelRun run;
        run.name = ref.name;
        vlt::TapeDoc tape;
        std::string fingerprint;
        if (!vlt::stage::load_tape(base + ref.bundle, ref.name, warm, tape, fingerprint)) {
            return 4;
        }
        run.event_count = static_cast<int>(tape.events.size());
        run.tag_span = vlt::stage::tag_span(tape);
        for (const QueryRef &q : ref.queries) {
            vlt::AnswerCell cell;
            cell.op = q.op;
            cell.from = q.from;
            cell.to = q.to;
            cell.at = q.at;
            cell.mask = q.mask;
            if (q.op == "fold") {
                cell.value = vlt::stage::fold_range(tape, q.from, q.to);
            } else if (q.op == "peek") {
                cell.value = vlt::stage::peek_at(tape, q.at);
            } else {
                cell.value = vlt::stage::tally_mask(tape, q.mask);
            }
            run.answers.push_back(cell);
        }
        run.row_digest = vlt::stage::panel_digest(run);
        vlt::stage::write_panel_checkpoint(ref.name, fingerprint, run.row_digest);
        doc.panels.push_back(std::move(run));
    }
    doc.digest = vlt::stage::campaign_digest(doc.schema_version, doc.campaign_id, doc.panels, panel_order);
    std::ofstream ofs(out_path);
    ofs << "{\n  \"schema_version\": " << doc.schema_version << ",\n";
    ofs << "  \"campaign_id\": " << json_escape(doc.campaign_id) << ",\n  \"panels\": [\n";
    for (size_t i = 0; i < doc.panels.size(); ++i) {
        const auto &run = doc.panels[i];
        ofs << "    {\n";
        ofs << "      \"name\": " << json_escape(run.name) << ",\n";
        ofs << "      \"event_count\": " << run.event_count << ",\n";
        ofs << "      \"tag_span\": " << run.tag_span << ",\n";
        ofs << "      \"answers\": [\n";
        for (size_t j = 0; j < run.answers.size(); ++j) {
            const auto &cell = run.answers[j];
            ofs << "        { \"op\": " << json_escape(cell.op);
            if (cell.op == "fold") {
                ofs << ", \"from\": " << cell.from << ", \"to\": " << cell.to;
            } else if (cell.op == "peek") {
                ofs << ", \"at\": " << cell.at;
            } else {
                ofs << ", \"mask\": " << cell.mask;
            }
            ofs << ", \"value\": " << cell.value << " }";
            ofs << (j + 1 < run.answers.size() ? "," : "") << "\n";
        }
        ofs << "      ],\n";
        ofs << "      \"row_digest\": " << json_escape(run.row_digest) << "\n";
        ofs << "    }" << (i + 1 < doc.panels.size() ? "," : "") << "\n";
    }
    ofs << "  ],\n  \"digest\": " << json_escape(doc.digest) << "\n}\n";
    return 0;
}
