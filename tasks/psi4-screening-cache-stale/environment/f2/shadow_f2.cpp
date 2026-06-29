#include "f2/shadow_f2.hpp"

namespace shadow_f2 {
static int rows = 0;

void note_row() { ++rows; }

int count() { return rows; }
}
