#!/bin/bash
# Reconciles append-only journal tail into the cap store before publish.
merge_tail() {
  ENV_ROOT="${ENV_ROOT:-/app/environment}"
  local journal="/app/work/cap_journal.tsv"
  local store="/app/work/cap_store.tsv"
  local best="/app/work/merge_best.tsv"
  local tmpstore="/app/work/cap_store.next.tsv"
  [[ -f "$journal" ]] || return 0
  awk -F'\t' '
    NF >= 10 {
      key = $2 SUBSEP $3 SUBSEP $4
      if (!(key in seq) || ($1 + 0) < seq[key]) {
        seq[key] = $1 + 0
        line[key] = $2 "\t" $3 "\t" $4 "\t" $5 "\t" $6 "\t" $7 "\t" $8 "\t" $9 "\t" $10 "\t" $1
      }
    }
    END {
      for (k in line) print line[k]
    }
  ' "$journal" > "$best"
  if [[ ! -s "$best" ]]; then
    return 0
  fi
  awk -F'\t' -v bestfile="$best" '
    BEGIN {
      while ((getline row < bestfile) > 0) {
        split(row, f, "\t")
        drop[f[1] SUBSEP f[2] SUBSEP f[3]] = 1
      }
      close(bestfile)
    }
    FNR == 1 && !($1 SUBSEP $2 SUBSEP $3 in drop) { print $0; next }
    !($1 SUBSEP $2 SUBSEP $3 in drop) { print $0 }
  ' "$store" 2>/dev/null > "$tmpstore" || : > "$tmpstore"
  cat "$best" >> "$tmpstore"
  mv "$tmpstore" "$store"
}
