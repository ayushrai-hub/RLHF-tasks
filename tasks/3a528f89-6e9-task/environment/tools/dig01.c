#include "dig01.h"

#include <stdio.h>
#include <string.h>

static uint64_t fnv1a64(const uint8_t *data, size_t len)
{
    uint64_t h = 14695981039346656037ULL;
    for (size_t i = 0; i < len; i++) {
        h ^= data[i];
        h *= 1099511628211ULL;
    }
    return h;
}

uint64_t dig01_fnv1a64(const uint8_t *data, size_t len)
{
    return fnv1a64(data, len);
}

static int read_note_payload(const char *path, uint8_t *out, size_t *olen)
{
    FILE *fp = fopen(path, "rb");
    if (!fp) {
        return -1;
    }
    unsigned char ident[16];
    if (fread(ident, 1, 16, fp) != 16 || ident[0] != 0x7f) {
        fclose(fp);
        return -2;
    }
    unsigned char e_phoff_raw[8];
    fseek(fp, 32, SEEK_SET);
    if (fread(e_phoff_raw, 1, 8, fp) != 8) {
        fclose(fp);
        return -3;
    }
    uint64_t phoff = 0;
    memcpy(&phoff, e_phoff_raw, 8);
    fseek(fp, (long)phoff, SEEK_SET);
    unsigned char ph[56];
    if (fread(ph, 1, 56, fp) != 56) {
        fclose(fp);
        return -4;
    }
    uint32_t p_type = 0;
    uint64_t p_offset = 0;
    uint64_t p_filesz = 0;
    memcpy(&p_type, ph, 4);
    memcpy(&p_offset, ph + 8, 8);
    memcpy(&p_filesz, ph + 32, 8);
    if (p_type != 4 || p_filesz < 16) {
        fclose(fp);
        return -5;
    }
    fseek(fp, (long)p_offset, SEEK_SET);
    unsigned char note_hdr[12];
    if (fread(note_hdr, 1, 12, fp) != 12) {
        fclose(fp);
        return -6;
    }
    uint32_t namesz = 0;
    uint32_t descsz = 0;
    memcpy(&namesz, note_hdr, 4);
    memcpy(&descsz, note_hdr + 4, 4);
    if (descsz == 0 || descsz > 32) {
        fclose(fp);
        return -7;
    }
    (void)namesz;
    unsigned char name_pad[16];
    size_t name_read = namesz + ((4 - (namesz % 4)) % 4);
    if (name_read > sizeof(name_pad)) {
        fclose(fp);
        return -8;
    }
    if (fread(name_pad, 1, name_read, fp) != name_read) {
        fclose(fp);
        return -9;
    }
    if (fread(out, 1, descsz, fp) != descsz) {
        fclose(fp);
        return -10;
    }
    *olen = descsz;
    fclose(fp);
    return 0;
}

int dig01_note_bytes(const char *path, uint8_t *out, size_t *olen)
{
    return read_note_payload(path, out, olen);
}

int dig01_digest_hex(const char *path, char *hex, size_t hlen)
{
    uint8_t payload[32];
    size_t plen = 0;
    if (read_note_payload(path, payload, &plen) != 0) {
        return -1;
    }
    uint64_t d = fnv1a64(payload, plen);
    if (hlen < 17) {
        return -2;
    }
    snprintf(hex, hlen, "%016llx", (unsigned long long)(d & 0xffffffffffffULL));
    return 0;
}
