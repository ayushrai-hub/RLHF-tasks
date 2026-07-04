#ifndef GLYPHVAULT_TRANSCRIPT_WRITER_H
#define GLYPHVAULT_TRANSCRIPT_WRITER_H

#include <sqlite3.h>

#include "glyphvault/types.h"

int gv_write_transcript(const gv_transcript *t, const char *out_path);
int gv_persist_score(sqlite3 *db, const gv_state *st);

#endif
