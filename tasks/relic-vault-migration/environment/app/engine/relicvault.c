/* Relic Vault -- terminal roguelike engine (PARTIALLY IMPLEMENTED).
 *
 * Modes:
 *   relicvault --replay --pack <vault.pack> --script <file> [--out <file>]
 *   relicvault --play   --pack <vault.pack>          (interactive ncurses)
 *   relicvault --legacy                              (print legacy room table)
 *
 * The pack loader below reads the migrated database, but the replay engine does
 * NOT yet enforce the expedition rites (combat, relics, bracing, the transcript
 * format). Recover the rules from /app/docs/chronicle.md (Appendices III-IV) and
 * finish run_replay() so the transcript matches the chronicle exactly.
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

static int load_pack(const char *path, Chamber *chambers) {
    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (size < 12) { fclose(f); return -1; }
    unsigned char *buf = malloc((size_t)size);
    if (fread(buf, 1, (size_t)size, f) != (size_t)size) {
        free(buf); fclose(f); return -1;
    }
    fclose(f);
    if (memcmp(buf, "RVP1", 4) != 0) { free(buf); return -1; }
    unsigned count = ru32(buf + 4);
    for (unsigned i = 0; i < count && i < MAX_CHAMBERS; i++) {
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
    free(buf);
    return (int)count;
}

static int run_replay(const char *pack_path, const char *script_path, FILE *out) {
    Chamber *chambers = calloc(MAX_CHAMBERS, sizeof(Chamber));
    int count = load_pack(pack_path, chambers);
    if (count < 0) { free(chambers); return 1; }
    (void)script_path;
    /* TODO: read the script and simulate the expedition. For now we only list
     *       the chambers we loaded -- this is NOT the required transcript. */
    for (int i = 0; i < count; i++) {
        fprintf(out, "chamber %d: %s guard_hp=%d\n",
                i, chambers[i].name, chambers[i].guard_hp);
    }
    free(chambers);
    return 0;
}

static int run_legacy(void) {
    int n = legacy_room_count();
    printf("legacy room table (%d rooms):\n", n);
    for (int i = 0; i < n; i++)
        printf("  %d\t%s\n", legacy_room_id(i), legacy_room_name(i));
    return 0;
}

int main(int argc, char **argv) {
    const char *pack = NULL, *script = NULL, *out_path = NULL;
    int mode_replay = 0, mode_legacy = 0;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--replay") == 0) mode_replay = 1;
        else if (strcmp(argv[i], "--legacy") == 0) mode_legacy = 1;
        else if (strcmp(argv[i], "--pack") == 0 && i + 1 < argc) pack = argv[++i];
        else if (strcmp(argv[i], "--script") == 0 && i + 1 < argc) script = argv[++i];
        else if (strcmp(argv[i], "--out") == 0 && i + 1 < argc) out_path = argv[++i];
    }
    if (mode_legacy) return run_legacy();
    if (mode_replay) {
        if (!pack || !script) { fprintf(stderr, "--replay needs --pack and --script\n"); return 2; }
        FILE *out = out_path ? fopen(out_path, "w") : stdout;
        if (!out) return 1;
        int rc = run_replay(pack, script, out);
        if (out != stdout) fclose(out);
        return rc;
    }
    fprintf(stderr, "usage: %s --replay --pack <f> --script <f> [--out <f>]\n", argv[0]);
    return 2;
}
