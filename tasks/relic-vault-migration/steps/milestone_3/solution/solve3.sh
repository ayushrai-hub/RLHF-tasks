#!/bin/bash
# Milestone 3 -- Integrate Terminal Expedition.
# Extends the C engine to load vault.pack and enforce the expedition rites, then
# builds it and replays the scripted expedition into the transcript.
set -euo pipefail
mkdir -p /app/out

cat > /app/engine/relicvault.c <<'RELICVAULT_C_EOF'
/* Relic Vault -- terminal roguelike engine.
 *
 * Modes:
 *   relicvault --replay --pack <vault.pack> --script <file> [--out <file>]
 *       Headless replay of a scripted expedition; writes the transcript.
 *   relicvault --play --pack <vault.pack>
 *       Interactive ncurses descent (not used by the automated verifier).
 *   relicvault --legacy
 *       Print the legacy hand-written room table.
 *
 * The migrated database format and the expedition rites are described in
 * /app/docs/chronicle.md (Appendices III and IV).
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "legacy_rooms.h"

#define MAX_CHAMBERS 4096
#define REC_SIZE 53
#define NAME_WIDTH 24
#define SPECIES_WIDTH 16

typedef struct {
    int room_id;
    int chamber_index;
    int guard_hp;
    int guard_atk;
    int relic_worth;
    int hazard;
    int biome_code;
    char sigil;
    char name[NAME_WIDTH + 1];
    char species[SPECIES_WIDTH + 1];
} Chamber;

static unsigned ru16(const unsigned char *p) {
    return (unsigned)p[0] | ((unsigned)p[1] << 8);
}
static int ri16(const unsigned char *p) {
    int v = (int)p[0] | ((int)p[1] << 8);
    if (v & 0x8000) v -= 0x10000;
    return v;
}
static unsigned ru32(const unsigned char *p) {
    return (unsigned)p[0] | ((unsigned)p[1] << 8) |
           ((unsigned)p[2] << 16) | ((unsigned)p[3] << 24);
}

/* Load the pack image. Returns chamber count, or -1 on malformed input. */
static int load_pack(const char *path, Chamber *chambers) {
    FILE *f = fopen(path, "rb");
    if (!f) { fprintf(stderr, "cannot open pack: %s\n", path); return -1; }
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (size < 12) { fclose(f); return -1; }
    unsigned char *buf = malloc((size_t)size);
    if (!buf) { fclose(f); return -1; }
    if (fread(buf, 1, (size_t)size, f) != (size_t)size) {
        free(buf); fclose(f); return -1;
    }
    fclose(f);

    if (memcmp(buf, "RVP1", 4) != 0) { free(buf); return -1; }
    unsigned count = ru32(buf + 4);
    if (count > MAX_CHAMBERS) { free(buf); return -1; }
    long need = 8 + (long)REC_SIZE * count + 4;
    if (size != need) { free(buf); return -1; }

    for (unsigned i = 0; i < count; i++) {
        const unsigned char *r = buf + 8 + REC_SIZE * i;
        Chamber *c = &chambers[i];
        c->room_id = (int)ru16(r + 0);
        c->chamber_index = (int)ru16(r + 2);
        c->guard_hp = ri16(r + 4);
        c->guard_atk = ri16(r + 6);
        c->relic_worth = ri16(r + 8);
        c->hazard = r[10];
        c->biome_code = r[11];
        c->sigil = (char)r[12];
        memcpy(c->name, r + 13, NAME_WIDTH); c->name[NAME_WIDTH] = '\0';
        memcpy(c->species, r + 13 + NAME_WIDTH, SPECIES_WIDTH);
        c->species[SPECIES_WIDTH] = '\0';
    }
    if (memcmp(buf + 8 + REC_SIZE * count, "RVPE", 4) != 0) { free(buf); return -1; }
    free(buf);
    return (int)count;
}

static void strip_upper(char *s) {
    /* trim leading/trailing whitespace, uppercase in place */
    char *start = s;
    while (*start == ' ' || *start == '\t' || *start == '\r' || *start == '\n')
        start++;
    char *end = start + strlen(start);
    while (end > start && (end[-1] == ' ' || end[-1] == '\t' ||
                           end[-1] == '\r' || end[-1] == '\n'))
        end--;
    *end = '\0';
    size_t n = (size_t)(end - start);
    memmove(s, start, n + 1);
    for (size_t i = 0; i < n; i++)
        if (s[i] >= 'a' && s[i] <= 'z') s[i] = (char)(s[i] - 'a' + 'A');
}

static int run_replay(const char *pack_path, const char *script_path,
                      FILE *out) {
    Chamber *chambers = calloc(MAX_CHAMBERS, sizeof(Chamber));
    if (!chambers) return 1;
    int count = load_pack(pack_path, chambers);
    if (count < 0) { free(chambers); return 1; }

    FILE *sf = fopen(script_path, "r");
    if (!sf) { free(chambers); fprintf(stderr, "cannot open script\n"); return 1; }

    int *guard_rem = calloc(count > 0 ? count : 1, sizeof(int));
    char *taken = calloc(count > 0 ? count : 1, sizeof(char));
    for (int i = 0; i < count; i++) guard_rem[i] = chambers[i].guard_hp;

    int hp = 25, atk = 4, score = 0, pos = -1, max_pos = -1;
    int turn = 0, downed = 0, streak = 0;
    char line[512];
    char event[128];

    while (fgets(line, sizeof(line), sf)) {
        char work[512];
        strncpy(work, line, sizeof(work) - 1);
        work[sizeof(work) - 1] = '\0';
        strip_upper(work);
        if (work[0] == '\0' || work[0] == '#') continue;
        turn++;
        event[0] = '\0';

        if (strcmp(work, "ADVANCE") == 0) {
            if (pos < count - 1) {
                pos++;
                if (pos > max_pos) max_pos = pos;
                snprintf(event, sizeof(event), "enter %s", chambers[pos].name);
            } else {
                snprintf(event, sizeof(event), "EDGE");
            }
        } else if (strcmp(work, "STRIKE") == 0) {
            if (pos >= 0 && pos < count && guard_rem[pos] > 0) {
                guard_rem[pos] -= atk;
                if (guard_rem[pos] > 0) {
                    int dmg = chambers[pos].guard_atk;
                    hp -= dmg;
                    if (hp <= 0) {
                        /* Downing blow: hp pinned at 0, atk left unchanged. */
                        hp = 0; downed = 1;
                        snprintf(event, sizeof(event), "DOWNED -%d", dmg);
                    } else {
                        /* Survived wound: atk -1, floored at the starting 4. */
                        atk -= 1;
                        if (atk < 4) atk = 4;
                        snprintf(event, sizeof(event), "TRADE -%d", dmg);
                    }
                } else {
                    /* Slain: atk ratchets up by 1. */
                    atk += 1;
                    snprintf(event, sizeof(event), "SLAIN");
                }
            } else {
                snprintf(event, sizeof(event), "EMPTY");
            }
        } else if (strcmp(work, "GRAB") == 0) {
            if (pos >= 0 && pos < count && guard_rem[pos] <= 0 &&
                chambers[pos].relic_worth > 0 && !taken[pos]) {
                int worth = chambers[pos].relic_worth;
                score += worth;
                taken[pos] = 1;
                snprintf(event, sizeof(event), "CLAIM +%d", worth);
            } else {
                snprintf(event, sizeof(event), "WARDED");
            }
        } else if (strcmp(work, "BRACE") == 0) {
            int cap = 25;
            int heal = (hp + 3 < cap ? hp + 3 : cap) - hp;
            hp += heal;
            snprintf(event, sizeof(event), "BRACE +%d", heal);
        } else {
            snprintf(event, sizeof(event), "IDLE");
        }

        /* Kill-streak / slayer's tithe: a SLAIN extends the streak and pays the
         * new streak value into the score; any other event resets it to 0. */
        if (strcmp(event, "SLAIN") == 0) {
            streak += 1;
            score += streak;
        } else {
            streak = 0;
        }

        fprintf(out, "%03d %-7s pos=%+03d hp=%03d atk=%02d score=%05d | %s\n",
                turn, work, pos, hp, atk, score, event);
        if (downed) break;
    }
    fclose(sf);

    int cleared = 0;
    for (int i = 0; i < count; i++)
        if (i <= max_pos && guard_rem[i] <= 0) cleared++;
    const char *status = downed ? "DOWNED" : "ALIVE";
    fprintf(out, "RESULT status=%s hp=%03d atk=%02d score=%05d cleared=%02d turns=%03d\n",
            status, hp, atk, score, cleared, turn);

    free(guard_rem); free(taken); free(chambers);
    return 0;
}

#ifdef WITH_NCURSES
#include <ncurses.h>
static int run_play(const char *pack_path) {
    Chamber *chambers = calloc(MAX_CHAMBERS, sizeof(Chamber));
    int count = load_pack(pack_path, chambers);
    if (count < 0) { free(chambers); return 1; }
    initscr(); cbreak(); noecho(); keypad(stdscr, TRUE);
    int pos = 0;
    int ch;
    do {
        clear();
        mvprintw(0, 0, "Relic Vault -- chamber %d/%d: %s",
                 pos + 1, count, chambers[pos].name);
        mvprintw(2, 0, "guard_hp=%d guard_atk=%d relic_worth=%d sigil=%c",
                 chambers[pos].guard_hp, chambers[pos].guard_atk,
                 chambers[pos].relic_worth, chambers[pos].sigil);
        mvprintw(4, 0, "[n]ext  [p]rev  [q]uit");
        refresh();
        ch = getch();
        if (ch == 'n' && pos < count - 1) pos++;
        else if (ch == 'p' && pos > 0) pos--;
    } while (ch != 'q');
    endwin();
    free(chambers);
    return 0;
}
#endif

static int run_legacy(void) {
    int n = legacy_room_count();
    printf("legacy room table (%d rooms):\n", n);
    for (int i = 0; i < n; i++)
        printf("  %d\t%s\n", legacy_room_id(i), legacy_room_name(i));
    return 0;
}

int main(int argc, char **argv) {
    const char *pack = NULL, *script = NULL, *out_path = NULL;
    int mode_replay = 0, mode_play = 0, mode_legacy = 0;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--replay") == 0) mode_replay = 1;
        else if (strcmp(argv[i], "--play") == 0) mode_play = 1;
        else if (strcmp(argv[i], "--legacy") == 0) mode_legacy = 1;
        else if (strcmp(argv[i], "--pack") == 0 && i + 1 < argc) pack = argv[++i];
        else if (strcmp(argv[i], "--script") == 0 && i + 1 < argc) script = argv[++i];
        else if (strcmp(argv[i], "--out") == 0 && i + 1 < argc) out_path = argv[++i];
    }

    if (mode_legacy) return run_legacy();

    if (mode_play) {
#ifdef WITH_NCURSES
        if (!pack) { fprintf(stderr, "--play needs --pack\n"); return 2; }
        return run_play(pack);
#else
        fprintf(stderr, "built without ncurses; use --replay\n");
        return 2;
#endif
    }

    if (mode_replay) {
        if (!pack || !script) {
            fprintf(stderr, "--replay needs --pack and --script\n");
            return 2;
        }
        FILE *out = stdout;
        if (out_path) {
            out = fopen(out_path, "w");
            if (!out) { fprintf(stderr, "cannot open out\n"); return 1; }
        }
        int rc = run_replay(pack, script, out);
        if (out != stdout) fclose(out);
        return rc;
    }

    fprintf(stderr, "usage: %s --replay --pack <f> --script <f> [--out <f>]\n",
            argv[0]);
    return 2;
}
RELICVAULT_C_EOF

cat > /app/engine/legacy_rooms.c <<'LEGACY_C_EOF'
/* Legacy hand-written room table. This is the small, pre-migration loader the
 * engine used before the season-archive arrived; the migrated vault.pack
 * supersedes it for replay and play modes. */

#include "legacy_rooms.h"

typedef struct {
    int id;
    const char *name;
} LegacyRoom;

static const LegacyRoom LEGACY_ROOMS[] = {
    {1, "Old Cistern"},
    {2, "Collapsed Stair"},
    {3, "Tallow Vestibule"},
    {4, "Forgotten Oratory"},
};

int legacy_room_count(void) {
    return (int)(sizeof(LEGACY_ROOMS) / sizeof(LEGACY_ROOMS[0]));
}

int legacy_room_id(int index) {
    if (index < 0 || index >= legacy_room_count()) return -1;
    return LEGACY_ROOMS[index].id;
}

const char *legacy_room_name(int index) {
    if (index < 0 || index >= legacy_room_count()) return "?";
    return LEGACY_ROOMS[index].name;
}
LEGACY_C_EOF

cat > /app/engine/legacy_rooms.h <<'LEGACY_H_EOF'
#ifndef LEGACY_ROOMS_H
#define LEGACY_ROOMS_H

/* Legacy hand-written room table (pre-migration). Retained for the --legacy
 * inspector and the interactive --play fallback. */
int legacy_room_count(void);
int legacy_room_id(int index);
const char *legacy_room_name(int index);

#endif /* LEGACY_ROOMS_H */
LEGACY_H_EOF

cat > /app/engine/Makefile <<'MAKEFILE_EOF'
CC      ?= gcc
CFLAGS  ?= -O2 -std=c11 -Wall -Wextra -DWITH_NCURSES
LDLIBS  ?= -lncurses

OBJ = relicvault.o legacy_rooms.o

relicvault: $(OBJ)
	$(CC) $(CFLAGS) -o relicvault $(OBJ) $(LDLIBS)

relicvault.o: relicvault.c legacy_rooms.h
	$(CC) $(CFLAGS) -c -o $@ relicvault.c

legacy_rooms.o: legacy_rooms.c legacy_rooms.h
	$(CC) $(CFLAGS) -c -o $@ legacy_rooms.c

clean:
	rm -f $(OBJ) relicvault

.PHONY: clean
MAKEFILE_EOF

# Refresh the migrated database (harness completed in milestone 1).
python /app/harness/migrate.py pack --archive /app/archive --out /app/out

make -C /app/engine
/app/engine/relicvault --replay \
    --pack /app/out/vault.pack \
    --script /app/archive/expedition.script \
    --out /app/out/transcript.txt
