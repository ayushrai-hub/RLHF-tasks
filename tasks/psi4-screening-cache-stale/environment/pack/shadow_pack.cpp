#include "p7/epoch_row.hpp"
#include <iostream>
void shadow_pack_print(const p7::EpochRow& row) {
  std::cout << row.scenario << ' ' << row.view << '\n';
}
