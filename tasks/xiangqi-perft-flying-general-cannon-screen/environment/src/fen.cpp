#include "fen.hpp"

bool parse_fen(const std::string &placement, const std::string &side, State &s) {
    for (int i = 0; i < 90; i++) s.b[i] = 0;
    int r = 0, f = 0;
    for (char c : placement) {
        if (c == '/') { r++; f = 0; continue; }
        if (c >= '1' && c <= '9') { f += c - '0'; continue; }
        int type = 0;
        char u = (c >= 'a' && c <= 'z') ? (char)(c - 32) : c;
        switch (u) {
            case 'K': type = GENERAL; break;
            case 'A': type = ADVISOR; break;
            case 'B': case 'E': type = ELEPHANT; break;
            case 'N': case 'H': type = HORSE; break;
            case 'R': type = CHARIOT; break;
            case 'C': type = CANNON; break;
            case 'P': type = SOLDIER; break;
            default: return false;
        }
        int color = (c >= 'a' && c <= 'z') ? 1 : 0;
        if (r < 10 && f < 9) s.b[idx(r, f)] = enc(color, type);
        f++;
    }
    s.side = (side == "b") ? 1 : 0;
    return true;
}
