#include "glyphvault/glyph_atlas.h"

#include <png.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static png_bytep *rows = NULL;
static int img_w = 0;
static int img_h = 0;
static int tile_px = 8;

int gv_load_atlas(const char *png_path, int tile_size) {
    FILE *fp = fopen(png_path, "rb");
    if (!fp) return -1;
    png_structp png = png_create_read_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
    png_infop info = png_create_info_struct(png);
    if (!png || !info) {
        fclose(fp);
        return -1;
    }
    if (setjmp(png_jmpbuf(png))) {
        png_destroy_read_struct(&png, &info, NULL);
        fclose(fp);
        return -1;
    }
    png_init_io(png, fp);
    png_read_info(png, info);
    img_w = (int)png_get_image_width(png, info);
    img_h = (int)png_get_image_height(png, info);
    tile_px = tile_size;
    rows = (png_bytep *)malloc(sizeof(png_bytep) * (size_t)img_h);
    for (int y = 0; y < img_h; y++) {
        rows[y] = (png_bytep)malloc(png_get_rowbytes(png, info));
    }
    png_read_image(png, rows);
    png_destroy_read_struct(&png, &info, NULL);
    fclose(fp);
    return 0;
}

/* BROKEN: swaps atlas_col/atlas_row and uses 1-based coords without subtracting 1 */
char gv_sample_glyph(int atlas_col, int atlas_row) {
    if (!rows) return '?';
    int px = atlas_row * tile_px + tile_px / 2;
    int py = atlas_col * tile_px + tile_px / 2;
    if (px < 0 || py < 0 || px >= img_w || py >= img_h) return '?';
    png_bytep row = rows[py];
    return (char)row[px * 3];
}

void gv_unload_atlas(void) {
    if (!rows) return;
    for (int y = 0; y < img_h; y++) free(rows[y]);
    free(rows);
    rows = NULL;
}
