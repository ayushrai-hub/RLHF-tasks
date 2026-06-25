#include "types.hpp"

double shadow_center(const VecPack& u, const VecPack& v) {
    return (u.local_norm + v.local_norm) * 0.5;
}