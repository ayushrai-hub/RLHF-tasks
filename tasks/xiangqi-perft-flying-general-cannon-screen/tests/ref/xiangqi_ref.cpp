#include <cstdio>
#include <cstring>
#include <vector>
#include <string>
#include <sstream>
#include <iostream>
using namespace std;

static inline int idx(int r, int f) { return r * 9 + f; }
static inline bool onb(int r, int f) { return r >= 0 && r < 10 && f >= 0 && f < 9; }

struct State {
    signed char b[90];
    int stm;
};

static inline bool in_palace(int color, int r, int f) {
    if (f < 3 || f > 5) return false;
    if (color > 0) return r >= 7 && r <= 9;
    return r >= 0 && r <= 2;
}

struct Move { int from, to; };

static int find_general(const State &s, int color) {
    signed char g = (signed char)(color > 0 ? 1 : -1);
    for (int i = 0; i < 90; i++) if (s.b[i] == g) return i;
    return -1;
}

static bool generals_face(const State &s) {
    int rg = find_general(s, 1), bg = find_general(s, -1);
    if (rg < 0 || bg < 0) return false;
    int rf = rg % 9, bf = bg % 9;
    if (rf != bf) return false;
    int r0 = rg / 9, r1 = bg / 9;
    int lo = r0 < r1 ? r0 : r1, hi = r0 < r1 ? r1 : r0;
    for (int r = lo + 1; r < hi; r++) if (s.b[idx(r, rf)] != 0) return false;
    return true;
}

static bool attacked_by(const State &s, int tr, int tf, int by) {
    static const int dirs[4][2] = {{1,0},{-1,0},{0,1},{0,-1}};
    for (int d = 0; d < 4; d++) {
        int dr = dirs[d][0], df = dirs[d][1];
        int r = tr + dr, f = tf + df, seen = 0;
        while (onb(r, f)) {
            signed char p = s.b[idx(r, f)];
            if (p != 0) {
                int col = p > 0 ? 1 : -1, ty = p > 0 ? p : -p;
                if (seen == 0) {
                    if (col == by && ty == 5) return true;
#ifdef NO_CANNON
                    if (col == by && ty == 6) return true;
#endif
                    seen = 1;
                } else if (seen == 1) {
#ifndef NO_CANNON
                    if (col == by && ty == 6) return true;
#endif
                    break;
                }
            }
            r += dr; f += df;
        }
    }
    static const int hs[8][2] = {{2,1},{2,-1},{-2,1},{-2,-1},{1,2},{1,-2},{-1,2},{-1,-2}};
    for (int i = 0; i < 8; i++) {
        int hr = tr + hs[i][0], hf = tf + hs[i][1];
        if (!onb(hr, hf)) continue;
        signed char p = s.b[idx(hr, hf)];
        if (p == 0) continue;
        int col = p > 0 ? 1 : -1, ty = p > 0 ? p : -p;
        if (col != by || ty != 4) continue;
        int lr, lf;
        if (hs[i][0] == 2) { lr = hr - 1; lf = hf; }
        else if (hs[i][0] == -2) { lr = hr + 1; lf = hf; }
        else if (hs[i][1] == 2) { lr = hr; lf = hf - 1; }
        else { lr = hr; lf = hf + 1; }
        if (s.b[idx(lr, lf)] == 0) return true;
    }
    if (by > 0) {
        if (onb(tr + 1, tf) && s.b[idx(tr + 1, tf)] == 7) return true;
        if (tr <= 4) {
            if (onb(tr, tf - 1) && s.b[idx(tr, tf - 1)] == 7) return true;
            if (onb(tr, tf + 1) && s.b[idx(tr, tf + 1)] == 7) return true;
        }
    } else {
        if (onb(tr - 1, tf) && s.b[idx(tr - 1, tf)] == -7) return true;
        if (tr >= 5) {
            if (onb(tr, tf - 1) && s.b[idx(tr, tf - 1)] == -7) return true;
            if (onb(tr, tf + 1) && s.b[idx(tr, tf + 1)] == -7) return true;
        }
    }
    return false;
}

static bool in_check(const State &s, int side) {
    int g = find_general(s, side);
    if (g < 0) return true;
    if (attacked_by(s, g / 9, g % 9, -side)) return true;
#ifndef NO_FLYING
    if (generals_face(s)) return true;
#endif
    return false;
}

static void gen_pseudo(const State &s, vector<Move> &out) {
    int stm = s.stm;
    for (int r = 0; r < 10; r++) for (int f = 0; f < 9; f++) {
        signed char p = s.b[idx(r, f)];
        if (p == 0) continue;
        int col = p > 0 ? 1 : -1;
        if (col != stm) continue;
        int ty = p > 0 ? p : -p;
        int from = idx(r, f);
        auto emptyOrEnemy = [&](int tr, int tf) {
            signed char q = s.b[idx(tr, tf)];
            return q == 0 || (q > 0 ? 1 : -1) != stm;
        };
        if (ty == 1) {
            static const int od[4][2] = {{1,0},{-1,0},{0,1},{0,-1}};
            for (int d = 0; d < 4; d++) {
                int tr = r + od[d][0], tf = f + od[d][1];
                if (in_palace(stm, tr, tf) && emptyOrEnemy(tr, tf)) out.push_back({from, idx(tr, tf)});
            }
        } else if (ty == 2) {
            static const int od[4][2] = {{1,1},{1,-1},{-1,1},{-1,-1}};
            for (int d = 0; d < 4; d++) {
                int tr = r + od[d][0], tf = f + od[d][1];
                if (in_palace(stm, tr, tf) && emptyOrEnemy(tr, tf)) out.push_back({from, idx(tr, tf)});
            }
        } else if (ty == 3) {
            static const int od[4][2] = {{2,2},{2,-2},{-2,2},{-2,-2}};
            for (int d = 0; d < 4; d++) {
                int tr = r + od[d][0], tf = f + od[d][1];
                if (!onb(tr, tf)) continue;
                if (stm > 0 && tr < 5) continue;
                if (stm < 0 && tr > 4) continue;
                int er = r + od[d][0] / 2, ef = f + od[d][1] / 2;
                if (s.b[idx(er, ef)] != 0) continue;
                if (emptyOrEnemy(tr, tf)) out.push_back({from, idx(tr, tf)});
            }
        } else if (ty == 4) {
            static const int hs[8][2] = {{2,1},{2,-1},{-2,1},{-2,-1},{1,2},{1,-2},{-1,2},{-1,-2}};
            for (int i = 0; i < 8; i++) {
                int tr = r + hs[i][0], tf = f + hs[i][1];
                if (!onb(tr, tf)) continue;
                int lr, lf;
                if (hs[i][0] == 2) { lr = r + 1; lf = f; }
                else if (hs[i][0] == -2) { lr = r - 1; lf = f; }
                else if (hs[i][1] == 2) { lr = r; lf = f + 1; }
                else { lr = r; lf = f - 1; }
                if (s.b[idx(lr, lf)] != 0) continue;
                if (emptyOrEnemy(tr, tf)) out.push_back({from, idx(tr, tf)});
            }
        } else if (ty == 5) {
            static const int od[4][2] = {{1,0},{-1,0},{0,1},{0,-1}};
            for (int d = 0; d < 4; d++) {
                int tr = r + od[d][0], tf = f + od[d][1];
                while (onb(tr, tf)) {
                    signed char q = s.b[idx(tr, tf)];
                    if (q == 0) { out.push_back({from, idx(tr, tf)}); }
                    else { if ((q > 0 ? 1 : -1) != stm) out.push_back({from, idx(tr, tf)}); break; }
                    tr += od[d][0]; tf += od[d][1];
                }
            }
        } else if (ty == 6) {
            static const int od[4][2] = {{1,0},{-1,0},{0,1},{0,-1}};
            for (int d = 0; d < 4; d++) {
                int tr = r + od[d][0], tf = f + od[d][1];
                while (onb(tr, tf) && s.b[idx(tr, tf)] == 0) { out.push_back({from, idx(tr, tf)}); tr += od[d][0]; tf += od[d][1]; }
#ifdef NO_CANNON
                if (onb(tr, tf)) {
                    signed char q = s.b[idx(tr, tf)];
                    if (q != 0 && (q > 0 ? 1 : -1) != stm) out.push_back({from, idx(tr, tf)});
                }
#else
                if (onb(tr, tf)) {
                    tr += od[d][0]; tf += od[d][1];
                    while (onb(tr, tf) && s.b[idx(tr, tf)] == 0) { tr += od[d][0]; tf += od[d][1]; }
                    if (onb(tr, tf)) {
                        signed char q = s.b[idx(tr, tf)];
                        if (q != 0 && (q > 0 ? 1 : -1) != stm) out.push_back({from, idx(tr, tf)});
                    }
                }
#endif
            }
        } else if (ty == 7) {
            int fwd = stm > 0 ? -1 : 1;
            int tr = r + fwd, tf = f;
            if (onb(tr, tf) && emptyOrEnemy(tr, tf)) out.push_back({from, idx(tr, tf)});
            bool crossed = stm > 0 ? (r <= 4) : (r >= 5);
            if (crossed) {
                if (onb(r, f - 1) && emptyOrEnemy(r, f - 1)) out.push_back({from, idx(r, f - 1)});
                if (onb(r, f + 1) && emptyOrEnemy(r, f + 1)) out.push_back({from, idx(r, f + 1)});
            }
        }
    }
}

static void legal_moves(const State &s, vector<Move> &out) {
    vector<Move> ps; ps.reserve(64);
    gen_pseudo(s, ps);
    int mover = s.stm;
    for (const Move &m : ps) {
        State ns = s;
        ns.b[m.to] = ns.b[m.from];
        ns.b[m.from] = 0;
        ns.stm = -s.stm;
        if (!in_check(ns, mover)) out.push_back(m);
    }
}

static long long perft(const State &s, int depth) {
    if (depth == 0) return 1;
    vector<Move> ms; ms.reserve(64);
    legal_moves(s, ms);
    if (depth == 1) return (long long)ms.size();
    long long n = 0;
    for (const Move &m : ms) {
        State ns = s;
        ns.b[m.to] = ns.b[m.from];
        ns.b[m.from] = 0;
        ns.stm = -s.stm;
        n += perft(ns, depth - 1);
    }
    return n;
}

static bool parse_fen(const string &placement, const string &side, State &s) {
    memset(s.b, 0, sizeof(s.b));
    int r = 0, f = 0;
    for (char c : placement) {
        if (c == '/') { r++; f = 0; continue; }
        if (c >= '1' && c <= '9') { f += c - '0'; continue; }
        int ty = 0;
        char u = c >= 'a' && c <= 'z' ? c - 32 : c;
        switch (u) {
            case 'K': ty = 1; break; case 'A': ty = 2; break; case 'B': ty = 3; break;
            case 'E': ty = 3; break; case 'N': ty = 4; break; case 'H': ty = 4; break;
            case 'R': ty = 5; break; case 'C': ty = 6; break; case 'P': ty = 7; break;
            default: return false;
        }
        int col = (c >= 'a' && c <= 'z') ? -1 : 1;
        if (r < 10 && f < 9) s.b[idx(r, f)] = (signed char)(col * ty);
        f++;
    }
    s.stm = (side == "b") ? -1 : 1;
    return true;
}

int main() {
    string placement, side;
    int depth;
    if (!(cin >> placement >> side >> depth)) return 1;
    State s;
    if (!parse_fen(placement, side, s)) { printf("0\n"); return 0; }
    printf("%lld\n", perft(s, depth));
    return 0;
}
