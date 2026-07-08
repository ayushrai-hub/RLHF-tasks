#!/bin/bash
cd "$(dirname "$0")"
make >/dev/null 2>&1 || { echo "build failed"; exit 1; }
pass=0
fail=0
for fpath in data/start_positions.txt data/sanity_positions.txt data/quiet_positions.txt; do
  while read -r placement side depth expected; do
    [ -z "$placement" ] && continue
    got=$(printf '%s %s %s\n' "$placement" "$side" "$depth" | ./perft)
    if [ "$got" = "$expected" ]; then
      pass=$((pass+1))
    else
      fail=$((fail+1))
      echo "FAIL: $placement $side $depth got=$got want=$expected"
    fi
  done < "$fpath"
done
echo "passed=$pass failed=$fail"
