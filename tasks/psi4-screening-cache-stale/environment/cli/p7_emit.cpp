#include "p7/engine.hpp"
#include <iostream>
#include <string>
int main(int argc, char** argv) {
  std::string out = "/app/output/p7_trace.json";
  for (int i=1;i<argc;++i) if (std::string(argv[i])=="--out" && i+1<argc) out=argv[++i];
  try {
    auto digest = p7::emit_out(out);
    std::cout << "body_digest=" << digest << '\n';
  } catch (const std::exception& e) {
    std::cerr << "p7_emit: " << e.what() << '\n';
    return 1;
  }
  return 0;
}
