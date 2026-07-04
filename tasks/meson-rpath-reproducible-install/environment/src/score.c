#include "internal.h"

int cap_clamp_bucket(int weight) {
    if (weight < 0) {
        return 0;
    }
    if (weight < 500) {
        return 1;
    }
    if (weight < 900) {
        return 2;
    }
    if (weight < 1400) {
        return 3;
    }
    return 4;
}
