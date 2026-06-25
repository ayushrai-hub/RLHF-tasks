#include "types.h"

namespace vlt {
namespace stage {
void reset_lanes();
bool load_tape(const std::string &path, const std::string &panel_name, bool warm, TapeDoc &out,
               std::string &fingerprint_out);
std::int64_t fold_range(const TapeDoc &doc, int from, int to);
std::int64_t peek_at(const TapeDoc &doc, int at);
int tally_mask(const TapeDoc &doc, int mask);
int tag_span(const TapeDoc &doc);
std::string row_serial(const PanelRun &run);
std::string panel_digest(const PanelRun &run);
std::string campaign_digest(int schema_version, const std::string &campaign_id,
                            const std::vector<PanelRun> &panels,
                            const std::vector<std::string> &panel_order);
void write_panel_checkpoint(const std::string &panel_name, const std::string &tape_fp,
                            const std::string &row_digest);
void reset_journal();
std::string journal_tail(const std::vector<std::string> &panel_order);
}  // namespace stage
}  // namespace vlt
