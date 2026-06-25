#ifndef CAP_JOURNAL_H
#define CAP_JOURNAL_H

#include "cap_layout.h"

int cap_journal_append(const cap_row_t *row);
int cap_journal_tail_seq(const char *round, const char *actor, const char *mark, unsigned *out_seq);

#endif
