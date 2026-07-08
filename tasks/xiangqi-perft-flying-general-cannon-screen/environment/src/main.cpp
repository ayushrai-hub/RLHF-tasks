#include "fen.hpp"
#include "perft.hpp"
#include <iostream>
#include <cstdio>
#include <string>

int main() {
    std::string placement, side;
    int depth;
    if (!(std::cin >> placement >> side >> depth)) { std::printf("0\n"); return 0; }
    State s;
    if (!parse_fen(placement, side, s)) { std::printf("0\n"); return 0; }
    std::printf("%lld\n", perft(s, depth));
    return 0;
}
