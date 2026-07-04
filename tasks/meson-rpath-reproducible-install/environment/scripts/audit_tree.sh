#!/usr/bin/env bash
set -eu

prefix=${1:?install prefix required}
manifest=${2:?manifest output required}
ambient_lib=${3:?ambient library directory required}
ledger_path=${4:?ledger path required}
pipeline_mode=${5:?pipeline mode required}

bin_rel="bin/capsule-info"
header_rel="include/capsule_config.h"
bin_path="$prefix/$bin_rel"
header_path="$prefix/$header_rel"
mkdir -p "$(dirname "$manifest")"

json_string() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/$/"/; s/^/"/'
}

kv_value() {
  key=$1
  awk -F= -v want="$key" '$1 == want {print substr($0, length($1) + 2); exit}'
}

extract_define() {
  name=$1
  awk -v want="$name" '$1 == "#define" && $2 == want {gsub(/^"|"$/, "", $3); print $3; exit}' "$header_path"
}

read_path_note() {
  readelf -d "$bin_path" 2>/dev/null | awk -F'[][]' '/RPATH|RUNPATH/ {print $2; exit}'
}

run_installed() {
  LD_LIBRARY_PATH="$ambient_lib:$prefix/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "$bin_path"
}

runtime_output=$(run_installed)
compiled_package_id=$(printf '%s\n' "$runtime_output" | kv_value compiled_package_id)
compiled_version=$(printf '%s\n' "$runtime_output" | kv_value compiled_version)
compiled_source=$(printf '%s\n' "$runtime_output" | kv_value compiled_source)
compiled_provenance=$(printf '%s\n' "$runtime_output" | kv_value compiled_provenance)
linked_package_id=$(printf '%s\n' "$runtime_output" | kv_value linked_package_id)
linked_version=$(printf '%s\n' "$runtime_output" | kv_value linked_version)
linked_source=$(printf '%s\n' "$runtime_output" | kv_value linked_source)
linked_provenance=$(printf '%s\n' "$runtime_output" | kv_value linked_provenance)
linked_origin=$(printf '%s\n' "$runtime_output" | kv_value linked_origin)
header_sha=$(sha256sum "$header_path" | awk '{print $1}')
run_path=$(read_path_note || true)
catalog_epoch=$(extract_define CAPSULE_CATALOG_PROFILE)

tree_root=$(python3 - <<'PY' "$prefix"
import hashlib, os, subprocess, sys
prefix = sys.argv[1]
rows = []
for root, _dirs, names in os.walk(prefix):
    for name in names:
        path = os.path.join(root, name)
        rel = os.path.relpath(path, prefix)
        digest = subprocess.check_output(["sha256sum", path], text=True).split()[0]
        rows.append(f"{rel}:{digest}")
rows.sort()
print(hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest())
PY
)

if [ "$pipeline_mode" = "fresh" ]; then
  if [ -f "$ledger_path" ]; then
    ledger_generation=$(python3 - <<'PY' "$ledger_path"
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    print(int(json.load(handle).get("generation", 0)) + 1)
PY
)
  else
    ledger_generation=1
  fi
else
  if [ -f "$ledger_path" ]; then
    ledger_generation=$(python3 - <<'PY' "$ledger_path"
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    print(int(json.load(handle).get("generation", 1)) + 1)
PY
)
  else
    ledger_generation=1
  fi
fi

{
  printf '{\n'
  printf '  "schema": "capsule-install-manifest-v1",\n'
  printf '  "prefix": %s,\n' "$(json_string "$prefix")"
  printf '  "build_system": "meson",\n'
  printf '  "ledger": {\n'
  printf '    "generation": %s,\n' "$ledger_generation"
  printf '    "catalog_epoch": %s,\n' "$(json_string "$catalog_epoch")"
  printf '    "tree_root_sha256": %s\n' "$(json_string "$tree_root")"
  printf '  },\n'
  printf '  "runtime": {\n'
  printf '    "binary": %s,\n' "$(json_string "$bin_rel")"
  printf '    "ld_library_path": %s,\n' "$(json_string "$ambient_lib:$prefix/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}")"
  printf '    "rpath": %s,\n' "$(json_string "$run_path")"
  printf '    "compiled": {"package_id": %s, "version": %s, "source": %s, "provenance": %s},\n' \
    "$(json_string "$compiled_package_id")" "$(json_string "$compiled_version")" "$(json_string "$compiled_source")" "$(json_string "$compiled_provenance")"
  printf '    "linked": {"package_id": %s, "version": %s, "source": %s, "provenance": %s, "origin": %s}\n' \
    "$(json_string "$linked_package_id")" "$(json_string "$linked_version")" "$(json_string "$linked_source")" "$(json_string "$linked_provenance")" "$(json_string "$linked_origin")"
  printf '  },\n'
  printf '  "config": {\n'
  printf '    "header": %s,\n' "$(json_string "$header_rel")"
  printf '    "sha256": %s,\n' "$(json_string "$header_sha")"
  printf '    "version": %s,\n' "$(json_string "$(extract_define CAPSULE_VERSION)")"
  printf '    "package_id": %s,\n' "$(json_string "$(extract_define CAPSULE_PACKAGE_ID)")"
  printf '    "source": %s,\n' "$(json_string "$(extract_define CAPSULE_CONFIG_SOURCE)")"
  printf '    "provenance": %s\n' "$(json_string "$(extract_define CAPSULE_CONFIG_PROVENANCE)")"
  printf '  },\n'
  printf '  "tree": [\n'
  first=1
  while IFS= read -r file; do
    rel=${file#"$prefix"/}
    mode=$(stat -c '%a' "$file")
    digest=$(sha256sum "$file" | awk '{print $1}')
    if [ "$first" -eq 0 ]; then
      printf ',\n'
    fi
    first=0
    printf '    {"path": %s, "mode": %s, "sha256": %s}' \
      "$(json_string "$rel")" "$(json_string "$mode")" "$(json_string "$digest")"
  done < <(find "$prefix" -type f | sort)
  printf '\n  ]\n'
  printf '}\n'
} > "$manifest"

bash "$(dirname "$0")/install_ledger.sh" "$ledger_path" "$pipeline_mode" "$manifest" "$catalog_epoch"
