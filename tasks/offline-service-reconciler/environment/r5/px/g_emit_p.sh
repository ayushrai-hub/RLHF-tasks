#!/usr/bin/env bash
# Module C of the w7 toolchain.
# pack_c: read resolved rows on stdin, write inventory_out.json with each record's
# provenance and the derived digest, write the report ledger to
# reconcile_report.json, and call apply_ctl.sh for the report cross-check. Schemas
# and the digest formula are in run_contract.md.
pack_c() {
  local ENV_ROOT OUT SCRATCH canon
  ENV_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  OUT=/app/output; mkdir -p "$OUT"
  SCRATCH="$ENV_ROOT/r7/scratch"; mkdir -p "$SCRATCH"
  canon="$SCRATCH/canon.txt"

  local rec_json="" ret_json="" led_json=""
  local first_rec=1 first_ret=1 first_led=1
  local surv_lines="" ret_lines=""

  while IFS=$'\t' read -r id decision surf epoch role region cand; do
    [ -z "$id" ] && continue
    local inv_cands="" led_cands="" first_c=1 tok cs ce cr rest
    local toks
    IFS=';' read -ra toks <<< "$cand"
    for tok in "${toks[@]}"; do
      [ -z "$tok" ] && continue
      cs="${tok%%:*}"; rest="${tok#*:}"; ce="${rest%%:*}"; rest="${rest#*:}"; cr="${rest%%:*}"
      [ "$ce" = "-" ] && ce=0
      if [ "$first_c" -eq 1 ]; then first_c=0; else inv_cands="$inv_cands,"; led_cands="$led_cands,"; fi
      inv_cands="$inv_cands{\"surface\":\"$cs\",\"epoch\":$ce}"
      led_cands="$led_cands{\"surface\":\"$cs\",\"role\":\"$cr\",\"epoch\":$ce}"
    done

    if [ "$decision" = "retired" ]; then
      if [ "$first_ret" -eq 1 ]; then first_ret=0; else ret_json="$ret_json,"; fi
      ret_json="$ret_json{\"id\":\"$id\",\"removed_by\":\"r3\"}"
      ret_lines="$ret_lines"$'\n'"H:$id|RETIRED|S:r3"
      if [ "$first_led" -eq 1 ]; then first_led=0; else led_json="$led_json,"; fi
      led_json="$led_json{\"id\":\"$id\",\"accepted_surface\":null,\"role\":null,\"decision\":\"retired\",\"removed_by\":\"r3\",\"candidates\":[$led_cands]}"
    else
      if [ "$first_rec" -eq 1 ]; then first_rec=0; else rec_json="$rec_json,"; fi
      rec_json="$rec_json{\"id\":\"$id\",\"role\":\"$role\",\"region\":\"$region\",\"provenance\":{\"accepted\":{\"surface\":\"$surf\",\"epoch\":$epoch},\"candidates\":[$inv_cands]}}"
      surv_lines="$surv_lines"$'\n'"H:$id|R:$role|G:$region|S:$surf|E:$epoch"
      if [ "$first_led" -eq 1 ]; then first_led=0; else led_json="$led_json,"; fi
      led_json="$led_json{\"id\":\"$id\",\"accepted_surface\":\"$surf\",\"role\":\"$role\",\"decision\":\"$decision\",\"candidates\":[$led_cands]}"
    fi
  done

  local canonical
  canonical="$(printf '%s%s' "$surv_lines" "$ret_lines")"
  printf '%s' "$canonical" > "$canon"
  local digest
  digest="$(sha256sum "$canon" | awk '{print $1}')"

  printf '{\n  "schema_version": 1,\n  "records": [%s],\n  "retired": [%s],\n  "provenance_digest": "%s"\n}\n' \
    "$rec_json" "$ret_json" "$digest" > "$OUT/inventory_out.json"

  printf '{\n  "schema_version": 1,\n  "ledger": [%s],\n  "binding_digest": "__BINDING_DIGEST__"\n}\n' \
    "$led_json" > "$OUT/reconcile_report.json"

  "$ENV_ROOT/r5/apply_ctl.sh" "$canon" "$OUT/reconcile_report.json"
}
