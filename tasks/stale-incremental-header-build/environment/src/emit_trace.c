#include "lib_iface.h"

#include <stdio.h>
#include <string.h>

int sink_d(const struct trace_ctx *tx, const char *out_path) {
  if (!tx || !out_path) {
    return -1;
  }
  FILE *f = fopen(out_path, "w");
  if (!f) {
    return -1;
  }
  fputs("{\"rows\":[", f);
  for (int i = 0; i < tx->n_rows; i++) {
    const struct trace_row *r = &tx->rows[i];
    if (i) {
      fputc(',', f);
    }
    fprintf(
        f,
        "{\"plan_id\":\"%s\",\"target\":\"%s\",\"fast_digest_hex\":\"%s\","
        "\"pristine_digest_hex\":\"%s\",\"capability_tag\":\"%s\"}",
        r->plan_id, r->target, r->fast_hex, r->pristine_hex, r->cap_label);
  }
  fputs("]}\n", f);
  fclose(f);
  return 0;
}
