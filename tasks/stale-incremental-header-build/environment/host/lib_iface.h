#ifndef LIB_IFACE_H
#define LIB_IFACE_H

#include <stddef.h>
#include <stdint.h>
#include <sys/stat.h>

#define TB_MAX_DEPS 32
#define TB_MAX_SLOTS 16
#define TB_TAG_LEN 40
#define TB_ROOT_LEN 256

struct graph_ctx {
  char root[TB_ROOT_LEN];
};

struct edge_buf {
  char paths[TB_MAX_DEPS][TB_ROOT_LEN];
  int n;
};

struct slot_tbl {
  uint32_t gen[TB_MAX_SLOTS];
  char blobs[TB_MAX_SLOTS][TB_ROOT_LEN];
  int n;
};

struct trace_row {
  char plan_id[64];
  char target[64];
  char fast_hex[65];
  char pristine_hex[65];
  char cap_label[TB_TAG_LEN];
};

struct trace_ctx {
  struct trace_row *rows;
  int n_rows;
  int cap_rows;
};

struct ring_entry {
  char blob_path[TB_ROOT_LEN];
  uint32_t stored_gen;
  uint32_t live_gen;
  int gen_aligned;
};

struct ring_audit {
  struct ring_entry entries[TB_MAX_SLOTS];
  int n;
  int any_stale_gen;
};

struct journal_surface {
  char source_rel[TB_ROOT_LEN];
  int last_action_skip;
};

int sink_d(const struct trace_ctx *tx, const char *out_path);

void tb_paths_init(const char *env_root);
const char *tb_env_root(void);
const char *tb_var_root(void);
const char *tb_gen_hdr(void);
const char *tb_plan_path(void);
const char *tb_out_trace(void);

int tb_file_sha256_hex(const char *path, char *hex_out, size_t hex_cap);
int tb_read_cap_label(const char *bin_path, char *label, size_t cap);
int tb_render_gen_hdr(const char *cap_value);
int tb_compile_unit(const char *src_rel, const char *obj_rel, int skip_if_fresh);
int tb_link_target(const char *target, const char *obj_rel, const char *bin_rel);
int tb_pristine_tree(void);
int tb_fast_rebuild_targets(const char **targets, int n_targets);
int tb_pristine_rebuild_targets(const char **targets, int n_targets);

void tb_note_widget_dirty(void);
void tb_scan_deps_for_dirty(void);
int tb_mtime_fresh(const struct stat *src, const struct stat *obj);
int tb_slot_reuse_ok(struct slot_tbl *t, uint32_t gen, const char *blob_path);

void tb_compile_journal_reset(void);
void tb_compile_journal_set_mode(const char *mode);
int tb_emit_dep_audit(const char *target, const char *out_path);

void tb_ring_load(void);
void tb_ring_clear(void);
int tb_ring_lookup(const char *blob, uint32_t gen);
void tb_ring_note(const char *blob, uint32_t gen);
int tb_ring_audit(struct ring_audit *out);
uint32_t tb_live_hdr_gen(void);
int tb_journal_surface(struct journal_surface *out, const char *src_rel);

#endif
