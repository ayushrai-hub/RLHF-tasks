#include "perft.hpp"

long long perft(const State &s, int depth) {
    if (depth == 0) return 1;
    std::vector<Move> ms;
    legal_moves(s, ms);
    if (depth == 1) return (long long)ms.size();
    long long tot = 0;
    for (const Move &m : ms) {
        State ns = s;
        apply_move(ns, m);
        tot += perft(ns, depth - 1);
    }
    return tot;
}
