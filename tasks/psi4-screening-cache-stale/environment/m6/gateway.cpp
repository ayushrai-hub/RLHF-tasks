#include "m6/m6_c.hpp"
namespace m6_gateway {
int serve(const std::string& block, const std::string& leaf, const std::string& tab_label,
          const std::string& dep_sig, const std::vector<double>& vals, double target, bool cached) {
  return serve_block(block, leaf, tab_label, dep_sig, vals, target, cached);
}
void bust(uint32_t sid) { bust_store(sid); }
}
