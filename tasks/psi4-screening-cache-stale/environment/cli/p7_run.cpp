#include "p7/engine.hpp"
#include <cstdlib>
#include <iostream>
int main(int argc, char** argv) {
  bool cold = false; int scenario = -1;
  for (int i=1;i<argc;++i) {
    std::string a=argv[i];
    if (a=="--cold") cold=true;
    else if (a=="--scenario" && i+1<argc) scenario=std::stoi(argv[++i]);
  }
  try {
    if (scenario >= 0) {
      auto rows = p7::run_scenario(static_cast<uint32_t>(scenario), cold);
      for (auto& r : rows)
        std::cout << r.scenario << ' ' << r.view << ' ' << r.label << " era=" << r.era << " act=" << r.action_code << '\n';
    } else {
      p7::replay_all(cold);
    }
  } catch (const std::exception& e) {
    std::cerr << "p7_run: " << e.what() << '\n';
    return 1;
  }
  return 0;
}
