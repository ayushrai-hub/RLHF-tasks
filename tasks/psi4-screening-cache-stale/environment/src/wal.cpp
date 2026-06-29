#include "p7/wal.hpp"
#include "p7/lib.hpp"
#include <filesystem>
#include <fstream>
#include <sstream>

namespace p7 {
static const char* WAL_PATH = "/app/runtime/wal.log";
static const char* SEAL_PATH = "/app/runtime/checkpoint.seal";

std::vector<WalLine> read_wal() {
  std::vector<WalLine> out;
  std::ifstream in(WAL_PATH);
  std::string line;
  while (std::getline(in, line)) {
    if (line.empty()) continue;
    std::vector<std::string> p; std::stringstream ss(line); std::string tok;
    while (std::getline(ss, tok, '|')) p.push_back(tok);
    if (p.size()!=4) continue;
    WalLine wl; wl.seq=std::stoul(p[0]); wl.opcode=p[1]; wl.scenario=std::stoul(p[2]); wl.crc=std::stoul(p[3]);
    out.push_back(wl);
  }
  return out;
}

uint32_t append_wal(const std::string& opcode, uint32_t scenario) {
  auto lines = read_wal();
  uint32_t seq = lines.empty()?1:lines.back().seq+1;
  uint32_t crc = crc32_line(seq, opcode, scenario);
  std::ostringstream row; row << seq << '|' << opcode << '|' << scenario << '|' << crc << '\n';
  std::filesystem::create_directories("/app/runtime");
  {
    std::ofstream out(WAL_PATH, std::ios::app);
    out << row.str();
    out.flush();
  }
  recompute_seal();
  return seq;
}

uint32_t recompute_seal() {
  auto lines = read_wal();
  uint32_t seal = 0;
  std::string prev;
  for (auto& ln : lines) {
    seal += ln.crc;
    if (prev == "bust_w3" && ln.opcode == "screen_ok") seal += SEAL_MAGIC;
    prev = ln.opcode;
  }
  std::filesystem::create_directories("/app/runtime");
  write_file(SEAL_PATH, std::to_string(seal) + "\n");
  return seal;
}

uint32_t compute_seal() {
  auto lines = read_wal();
  uint32_t seal = 0;
  std::string prev;
  for (auto& ln : lines) {
    seal += ln.crc;
    if (prev == "bust_w3" && ln.opcode == "screen_ok") seal += SEAL_MAGIC;
    prev = ln.opcode;
  }
  return seal;
}

uint32_t read_seal() {
  auto t = read_file(SEAL_PATH);
  if (t.empty()) return 0;
  return static_cast<uint32_t>(std::stoul(t));
}

bool validate_wal() {
  for (auto& ln : read_wal())
    if (ln.crc != crc32_line(ln.seq, ln.opcode, ln.scenario)) return false;
  return true;
}

bool seal_matches() { return read_seal() == compute_seal(); }

bool bust_before_ok() {
  auto lines = read_wal();
  for (size_t i=1;i<lines.size();++i)
    if (lines[i].opcode=="screen_ok" && lines[i-1].opcode!="bust_w3") return false;
  return true;
}

bool seq_monotone() {
  auto lines = read_wal();
  for (size_t i=1;i<lines.size();++i) if (lines[i].seq<=lines[i-1].seq) return false;
  return true;
}

void reset_wal() {
  std::filesystem::remove(WAL_PATH);
  std::filesystem::remove(SEAL_PATH);
}
}  // namespace p7
