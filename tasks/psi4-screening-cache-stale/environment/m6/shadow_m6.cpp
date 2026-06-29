#include "m6/shadow_m6.hpp"

namespace shadow_m6 {
static int binds = 0;

void note_bind() { ++binds; }

int count() { return binds; }
}
