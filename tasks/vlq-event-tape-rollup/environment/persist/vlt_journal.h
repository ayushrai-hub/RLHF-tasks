#pragma once
#include <string>
#include <vector>

namespace vlt {
namespace journal {

void clear_all();
void write_checkpoint(const std::string &panel_name, const std::string &tape_fp, const std::string &row_digest);
std::string tail_binding(const std::vector<std::string> &panel_order);

}  // namespace journal
}  // namespace vlt
