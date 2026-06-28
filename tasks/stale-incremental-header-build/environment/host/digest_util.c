#include "lib_iface.h"

#include <stdio.h>
#include <string.h>

int tb_file_sha256_hex(const char *path, char *hex_out, size_t hex_cap) {
  if (!path || !hex_out || hex_cap < 65) {
    return -1;
  }
  char cmd[768];
  snprintf(
      cmd, sizeof cmd,
      "sha256sum '%s' 2>/dev/null | awk '{print $1}'", path);
  FILE *fp = popen(cmd, "r");
  if (!fp) {
    return -1;
  }
  if (!fgets(hex_out, (int)hex_cap, fp)) {
    pclose(fp);
    return -1;
  }
  pclose(fp);
  size_t n = strlen(hex_out);
  while (n > 0 && (hex_out[n - 1] == '\n' || hex_out[n - 1] == '\r')) {
    hex_out[--n] = '\0';
  }
  return 0;
}

int tb_read_cap_label(const char *bin_path, char *label, size_t cap) {
  if (!bin_path || !label || cap < 2) {
    return -1;
  }
  char cmd[768];
  snprintf(cmd, sizeof cmd, "'%s' 2>/dev/null", bin_path);
  FILE *fp = popen(cmd, "r");
  if (!fp) {
    return -1;
  }
  char line[128];
  if (!fgets(line, sizeof line, fp)) {
    pclose(fp);
    return -1;
  }
  pclose(fp);
  const char *pfx = "@CAP:";
  char *pos = strstr(line, pfx);
  if (!pos) {
    return -1;
  }
  pos += strlen(pfx);
  size_t n = strlen(pos);
  while (n > 0 && (pos[n - 1] == '\n' || pos[n - 1] == '\r')) {
    pos[--n] = '\0';
  }
  snprintf(label, cap, "%s", pos);
  return 0;
}
