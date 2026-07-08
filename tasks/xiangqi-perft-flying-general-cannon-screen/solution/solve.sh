#!/bin/bash
set -euo pipefail

cat > /app/src/movegen.cpp <<'EOF'
#include "movegen.hpp"

void apply_move(State &s, const Move &m) {
    s.b[m.to] = s.b[m.from];
    s.b[m.from] = 0;
    s.side ^= 1;
}

static int find_general(const State &s, int color) {
    int g = enc(color, GENERAL);
    for (int i = 0; i < 90; i++) if (s.b[i] == g) return i;
    return -1;
}

static bool generals_face(const State &s) {
    int rg = find_general(s, 0), bg = find_general(s, 1);
    if (rg < 0 || bg < 0) return false;
    int rf = rg % 9, bf = bg % 9;
    if (rf != bf) return false;
    int r0 = rg / 9, r1 = bg / 9;
    int lo = r0 < r1 ? r0 : r1, hi = r0 < r1 ? r1 : r0;
    for (int r = lo + 1; r < hi; r++) if (s.b[idx(r, rf)] != 0) return false;
    return true;
}

static bool attacked(const State &s, int tr, int tf, int by) {
    static const int od[4][2] = {{1,0},{-1,0},{0,1},{0,-1}};
    for (int d = 0; d < 4; d++) {
        int dr = od[d][0], df = od[d][1];
        int r = tr + dr, f = tf + df, seen = 0;
        while (onb(r, f)) {
            int p = s.b[idx(r, f)];
            if (p) {
                int c = col_of(p), t = type_of(p);
                if (seen == 0) {
                    if (c == by && t == CHARIOT) return true;
                    seen = 1;
                } else {
                    if (c == by && t == CANNON) return true;
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
        int p = s.b[idx(hr, hf)];
        if (!p || col_of(p) != by || type_of(p) != HORSE) continue;
        int lr, lf;
        if (hs[i][0] == 2) { lr = hr - 1; lf = hf; }
        else if (hs[i][0] == -2) { lr = hr + 1; lf = hf; }
        else if (hs[i][1] == 2) { lr = hr; lf = hf - 1; }
        else { lr = hr; lf = hf + 1; }
        if (s.b[idx(lr, lf)] == 0) return true;
    }
    int sp = enc(by, SOLDIER);
    if (by == 0) {
        if (onb(tr + 1, tf) && s.b[idx(tr + 1, tf)] == sp) return true;
        if (tr <= 4) {
            if (onb(tr, tf - 1) && s.b[idx(tr, tf - 1)] == sp) return true;
            if (onb(tr, tf + 1) && s.b[idx(tr, tf + 1)] == sp) return true;
        }
    } else {
        if (onb(tr - 1, tf) && s.b[idx(tr - 1, tf)] == sp) return true;
        if (tr >= 5) {
            if (onb(tr, tf - 1) && s.b[idx(tr, tf - 1)] == sp) return true;
            if (onb(tr, tf + 1) && s.b[idx(tr, tf + 1)] == sp) return true;
        }
    }
    return false;
}

static bool in_check(const State &s, int side) {
    int g = find_general(s, side);
    if (g < 0) return true;
    if (attacked(s, g / 9, g % 9, side ^ 1)) return true;
    if (generals_face(s)) return true;
    return false;
}

static void gen_pseudo(const State &s, std::vector<Move> &out) {
    int stm = s.side;
    for (int r = 0; r < 10; r++) for (int f = 0; f < 9; f++) {
        int p = s.b[idx(r, f)];
        if (!p || col_of(p) != stm) continue;
        int t = type_of(p);
        int from = idx(r, f);
        if (t == GENERAL) {
            static const int od[4][2] = {{1,0},{-1,0},{0,1},{0,-1}};
            for (int d = 0; d < 4; d++) {
                int tr = r + od[d][0], tf = f + od[d][1];
                if (!in_palace(stm, tr, tf)) continue;
                int q = s.b[idx(tr, tf)];
                if (q == 0 || col_of(q) != stm) out.push_back({from, idx(tr, tf)});
            }
        } else if (t == ADVISOR) {
            static const int od[4][2] = {{1,1},{1,-1},{-1,1},{-1,-1}};
            for (int d = 0; d < 4; d++) {
                int tr = r + od[d][0], tf = f + od[d][1];
                if (!in_palace(stm, tr, tf)) continue;
                int q = s.b[idx(tr, tf)];
                if (q == 0 || col_of(q) != stm) out.push_back({from, idx(tr, tf)});
            }
        } else if (t == ELEPHANT) {
            static const int od[4][2] = {{2,2},{2,-2},{-2,2},{-2,-2}};
            for (int d = 0; d < 4; d++) {
                int tr = r + od[d][0], tf = f + od[d][1];
                if (!onb(tr, tf)) continue;
                if (!own_half(stm, tr)) continue;
                int er = r + od[d][0] / 2, ef = f + od[d][1] / 2;
                if (s.b[idx(er, ef)] != 0) continue;
                int q = s.b[idx(tr, tf)];
                if (q == 0 || col_of(q) != stm) out.push_back({from, idx(tr, tf)});
            }
        } else if (t == HORSE) {
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
                int q = s.b[idx(tr, tf)];
                if (q == 0 || col_of(q) != stm) out.push_back({from, idx(tr, tf)});
            }
        } else if (t == CHARIOT) {
            static const int od[4][2] = {{1,0},{-1,0},{0,1},{0,-1}};
            for (int d = 0; d < 4; d++) {
                int tr = r + od[d][0], tf = f + od[d][1];
                while (onb(tr, tf)) {
                    int q = s.b[idx(tr, tf)];
                    if (q == 0) out.push_back({from, idx(tr, tf)});
                    else { if (col_of(q) != stm) out.push_back({from, idx(tr, tf)}); break; }
                    tr += od[d][0]; tf += od[d][1];
                }
            }
        } else if (t == CANNON) {
            static const int od[4][2] = {{1,0},{-1,0},{0,1},{0,-1}};
            for (int d = 0; d < 4; d++) {
                int tr = r + od[d][0], tf = f + od[d][1];
                while (onb(tr, tf) && s.b[idx(tr, tf)] == 0) { out.push_back({from, idx(tr, tf)}); tr += od[d][0]; tf += od[d][1]; }
                if (onb(tr, tf)) {
                    tr += od[d][0]; tf += od[d][1];
                    while (onb(tr, tf) && s.b[idx(tr, tf)] == 0) { tr += od[d][0]; tf += od[d][1]; }
                    if (onb(tr, tf)) {
                        int q = s.b[idx(tr, tf)];
                        if (q && col_of(q) != stm) out.push_back({from, idx(tr, tf)});
                    }
                }
            }
        } else if (t == SOLDIER) {
            int fr = fwd(stm);
            int tr = r + fr, tf = f;
            if (onb(tr, tf)) { int q = s.b[idx(tr, tf)]; if (q == 0 || col_of(q) != stm) out.push_back({from, idx(tr, tf)}); }
            if (crossed_river(stm, r)) {
                for (int df = -1; df <= 1; df += 2) {
                    int sf = f + df;
                    if (onb(r, sf)) { int q = s.b[idx(r, sf)]; if (q == 0 || col_of(q) != stm) out.push_back({from, idx(r, sf)}); }
                }
            }
        }
    }
}

void legal_moves(const State &s, std::vector<Move> &out) {
    std::vector<Move> ps;
    gen_pseudo(s, ps);
    int mover = s.side;
    for (const Move &m : ps) {
        State ns = s;
        ns.b[m.to] = ns.b[m.from];
        ns.b[m.from] = 0;
        ns.side = s.side ^ 1;
        if (!in_check(ns, mover)) out.push_back(m);
    }
}
EOF

cd /app
make
echo "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w 3" | ./perft
