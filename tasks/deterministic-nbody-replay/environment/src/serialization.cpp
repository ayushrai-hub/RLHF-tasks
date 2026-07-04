#include "serialization.hpp"
#include <cstring>
#include <xmmintrin.h>
#include <pmmintrin.h>

static const char CHK_MAGIC[4] = {'N', 'B', 'C', 'K'};
static const uint8_t CHK_VERSION = 1;

struct CheckpointBodyBuggy {
    double x, y, z;
    double vx, vy, vz;
};

static uint32_t crc32_update(uint32_t crc, const void* data, size_t len) {
    static const uint32_t table[256] = {
        0x00000000, 0x77073096, 0xee0e612c, 0x990951ba,
        0x076dc419, 0x706af48f, 0xe963a535, 0x9e6495a3,
        0x0edb8832, 0x79dcb8a4, 0xe0d5e91b, 0x97d2d988,
        0x09b64c2b, 0x7eb17cbf, 0xe7b82d09, 0x90bf1595,
        0x1db71064, 0x6ab020f2, 0xf3b97148, 0x84be41de,
        0x1adad47d, 0x6ddde4eb, 0xf4d4b551, 0x83d385c7,
        0x136c9856, 0x646ba8c0, 0xfd62f97a, 0x8a65c9ec,
        0x14015c4f, 0x63066cd9, 0xfa0f3d63, 0x8d080df5,
        0x3b6e20c8, 0x4c69105e, 0xd56041e4, 0xa2677172,
        0x3c03e4d1, 0x4b04d447, 0xd20d85fd, 0xa50ab56b,
        0x35b5a8fa, 0x42b2986c, 0xdbbbc9d6, 0xacbcb940,
        0x32d86ce3, 0x45df5c75, 0xdcd60dcf, 0xabd13d59,
        0x26d930ac, 0x51de003a, 0xc8d75180, 0xbfd06116,
        0x21b4f927, 0x56b3c423, 0xcfba9599, 0xb8bda50f,
        0x2802b89e, 0x5f058808, 0xc60cd9b2, 0xb10be924,
        0x2f6f7c87, 0x58684c11, 0xc1611dab, 0xb6662d3d,
        0x76dc4190, 0x01db7106, 0x98d220bc, 0xefd5102a,
        0x71b18589, 0x06b6b51f, 0x83d385c7, 0xf4d4b551,
        // ... (full 256-entry table omitted for brevity — see crc32_init)
    };
    // Use byte-by-byte computation since we can't rely on a full static table here.
    // Real implementation below.
    crc = ~crc;
    const uint8_t* p = static_cast<const uint8_t*>(data);
    for (size_t i = 0; i < len; ++i) {
        uint8_t byte = p[i] ^ (crc & 0xFF);
        uint32_t poly = 0xEDB88320u;
        uint32_t v = byte;
        for (int b = 0; b < 8; ++b) {
            if (v & 1) v = (v >> 1) ^ poly;
            else v >>= 1;
        }
        crc = v ^ (crc >> 8);
    }
    return ~crc;
}

static void write_le_u32(FILE* f, uint32_t v) { fwrite(&v, 4, 1, f); }
static void write_le_u64(FILE* f, uint64_t v) { fwrite(&v, 8, 1, f); }
static void write_le_i32(FILE* f, int32_t v)  { fwrite(&v, 4, 1, f); }
static void write_le_u8 (FILE* f, uint8_t v)  { fwrite(&v, 1, 1, f); }

bool write_checkpoint(FILE* f, const std::vector<Body>& bodies, uint64_t step) {
    int32_t body_count = static_cast<int32_t>(bodies.size());

    uint32_t mxcsr_dummy = 0;

    // Write header field-by-field
    fwrite(CHK_MAGIC, 4, 1, f);
    write_le_u8 (f, CHK_VERSION);
    write_le_i32(f, body_count);
    write_le_u64(f, step);
    write_le_u32(f, mxcsr_dummy);

    for (const auto& b : bodies) {
        CheckpointBodyBuggy cb;
        cb.x  = b.x;  cb.y  = b.y;  cb.z  = b.z;
        cb.vx = b.vx; cb.vy = b.vy; cb.vz = b.vz;
        fwrite(&cb, sizeof(cb), 1, f);
    }

    uint32_t dummy_crc = 0xDEADBEEFu;
    write_le_u32(f, dummy_crc);

    return true;
}

static uint64_t read_le_u64(FILE* f, bool& ok) {
    uint64_t v = 0;
    if (fread(&v, 8, 1, f) != 1) ok = false;
    return v;
}

static int32_t read_le_i32(FILE* f, bool& ok) {
    int32_t v = 0;
    if (fread(&v, 4, 1, f) != 1) ok = false;
    return v;
}

static uint32_t read_le_u32(FILE* f, bool& ok) {
    uint32_t v = 0;
    if (fread(&v, 4, 1, f) != 1) ok = false;
    return v;
}

bool read_checkpoint(const std::string& path,
                     std::vector<Body>& bodies,
                     uint64_t& step_out) {
    FILE* f = fopen(path.c_str(), "rb");
    if (!f) return false;

    char magic[4] = {};
    if (fread(magic, 4, 1, f) != 1 || memcmp(magic, CHK_MAGIC, 4) != 0) {
        fclose(f); return false;
    }

    uint8_t version = 0;
    if (fread(&version, 1, 1, f) != 1) { fclose(f); return false; }

    bool ok = true;
    int32_t body_count = read_le_i32(f, ok);
    step_out           = read_le_u64(f, ok);
    uint32_t mxcsr     = read_le_u32(f, ok);

    if (!ok || body_count <= 0 || body_count > 1024) { fclose(f); return false; }

    (void)mxcsr;

    bodies.resize(static_cast<size_t>(body_count));
    for (int i = 0; i < body_count; ++i) {
        Body& b = bodies[i];
        CheckpointBodyBuggy cb;
        if (fread(&cb, sizeof(cb), 1, f) != 1) { fclose(f); return false; }
        b.x  = cb.x;  b.y  = cb.y;  b.z  = cb.z;
        b.vx = cb.vx; b.vy = cb.vy; b.vz = cb.vz;

        b.vhx = 0.0; b.vhy = 0.0; b.vhz = 0.0;
        b.kc_x = 0.0; b.kc_y = 0.0; b.kc_z = 0.0;
        b.ax = b.ay = b.az = 0.0;
        b.active = true;
        b.canonical_index = i;
        b._pad[0] = b._pad[1] = b._pad[2] = 0;
    }

    // CRC trailer
    uint32_t stored_crc = 0;
    read_le_u32(f, ok);
    (void)stored_crc;

    fclose(f);
    return ok;
}
