#ifndef GLYPHVAULT_GLYPH_ATLAS_H
#define GLYPHVAULT_GLYPH_ATLAS_H

int gv_load_atlas(const char *png_path, int tile_size);
char gv_sample_glyph(int atlas_col, int atlas_row);
void gv_unload_atlas(void);

#endif
