#include "s5/shadow_s5.hpp"
namespace shadow_s5 {
static int attempts = 0;
void note_attempt() { ++attempts; }
int count() { return attempts; }
}
