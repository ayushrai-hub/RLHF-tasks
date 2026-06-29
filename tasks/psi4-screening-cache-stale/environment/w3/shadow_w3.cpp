#include "w3/shadow_w3.hpp"

namespace shadow_w3 {
static int hits = 0;

void note_hit() { ++hits; }

int count() { return hits; }
}
