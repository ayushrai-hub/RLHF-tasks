#include "p7/scn_snap.hpp"
#include "p7/lib.hpp"
#include <map>
#include <sstream>

namespace p7 {
static std::map<std::string,std::string> parse_kv(const std::string& path) {
  std::map<std::string,std::string> m;
  std::istringstream in(read_file(path));
  std::string line;
  while (std::getline(in, line)) {
    if (line.empty() || line[0]=='#') continue;
    auto p = line.find('=');
    if (p==std::string::npos) continue;
    m[line.substr(0,p)] = line.substr(p+1);
  }
  return m;
}
static uint32_t u32(const std::map<std::string,std::string>& m, const char* k, uint32_t d=1) {
  auto it=m.find(k); return it==m.end()?d:static_cast<uint32_t>(std::stoul(it->second));
}
static double f64(const std::map<std::string,std::string>& m, const char* k, double d=0.01) {
  auto it=m.find(k); return it==m.end()?d:std::stod(it->second);
}
static std::string str(const std::map<std::string,std::string>& m, const char* k, const char* d) {
  auto it=m.find(k); return it==m.end()?d:it->second;
}
ScnSnap load_scn(const std::string& path) {
  auto m=parse_kv(path); ScnSnap s;
  s.principal=str(m,"principal","brz");
  s.tab_era=u32(m,"screen_gen",1);
  s.dep_era=u32(m,"swap_gen",1);
  s.live_era=u32(m,"live_gen",1);
  s.block_val=f64(m,"block_val",0.01);
  s.tranche=u32(m,"tranche",0);
  s.deny=u32(m,"deny",0);
  s.readopt=u32(m,"readopt",0);
  s.worker_steps=u32(m,"worker_steps",2);
  s.tab_label=str(m,"tab_label","k0");
  s.feed_era=u32(m,"feed_era",1);
  return s;
}
ScnSnap load_dep(const std::string& path) {
  auto m=parse_kv(path); ScnSnap s;
  s.dep_sig=str(m,"dep_sig","sig0");
  s.dep_era=u32(m,"swap_gen",1);
  s.rotation=u32(m,"rotation",1);
  return s;
}
std::vector<double> load_col_values(const std::string& path) {
  std::vector<double> out;
  for (auto& line : parse_kv(path)) {}
  auto text=read_file(path);
  std::istringstream in(text); std::string line;
  while (std::getline(in,line)) {
    if (line.rfind("values=",0)==0) {
      std::istringstream vs(line.substr(7)); std::string tok;
      while (std::getline(vs,tok,',')) out.push_back(std::stod(tok));
    }
  }
  if (out.empty()) out={0.1,0.2,0.3};
  return out;
}
}  // namespace p7
