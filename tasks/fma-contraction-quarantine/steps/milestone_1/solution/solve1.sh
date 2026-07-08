#!/usr/bin/env bash
# Milestone 1 oracle: build the strict and release profiles, then for each
# kernel run a structured probe under both and record bit-level divergence.
set -euo pipefail
cd /app
mkdir -p output

REL="-ffp-contract=fast -fassociative-math -freciprocal-math -fno-signed-zeros -fno-trapping-math -ffinite-math-only"
STR="-ffp-contract=off"

build() {
    local out=$1 fp=$2 o=""
    local tu
    for tu in geom helpers accum gain guard flux; do
        gcc -O2 -mfma $fp -Iinclude -c "src/$tu.c" -o "/tmp/$tu.o"
        o="$o /tmp/$tu.o"
    done
    gcc -O2 -mfma -Iinclude -c tools/kerneltest.c -o /tmp/kt.o
    gcc -O2 -mfma -o "$out" $o /tmp/kt.o -lm
}

build /tmp/kt_strict "$STR"
build /tmp/kt_release "$REL"

json_array() {
    local out="[" i=0 x
    for x in "$@"; do
        [ $i -gt 0 ] && out="$out, "
        out="$out$x"; i=1
    done
    echo "$out]"
}

emit() {
    local k=$1; shift
    local s r
    s=$(/tmp/kt_strict "$k" "$@")
    r=$(/tmp/kt_release "$k" "$@")
    [ $FIRST -eq 0 ] && printf ',\n'
    FIRST=0
    if [ "$s" != "$r" ]; then
        printf '  "%s": {"diverges": true, "witness": %s}' "$k" "$(json_array "$@")"
    else
        printf '  "%s": {"diverges": false}' "$k"
    fi
}

FIRST=1
{
    printf '{\n'
    emit cross2 0.1 0.3 0.1 0.3
    emit clamp01 0.5
    emit recover 1e16 1.0
    emit sign_of -3.0
    emit cascade 7.0 5.0 3.0
    emit roundtrip_residual 49.0
    emit polarity 1.0 1.0
    emit magdiff 0.1 0.1
    emit domain_guard 0.0 0.0
    emit horner 0.3
    printf '\n}\n'
} > output/result_1.json

cat output/result_1.json
