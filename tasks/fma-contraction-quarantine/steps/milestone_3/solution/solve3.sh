#!/usr/bin/env bash
# Milestone 3 oracle: for each kernel that breaches under release, bisect over
# (translation unit, flag) pairs to find the single suppression that restores
# the invariant, trying the kernel's own unit and the shared helper unit. The
# union of those minimal pairs is the suppression manifest.
set -euo pipefail
cd /app
mkdir -p output

REL="-ffp-contract=fast -fassociative-math -freciprocal-math -fno-signed-zeros -fno-trapping-math -ffinite-math-only"
STR="-ffp-contract=off"

build_uniform() {
    local out=$1 fp=$2 o=""
    local tu
    for tu in geom helpers accum gain guard flux; do
        gcc -O2 -mfma $fp -Iinclude -c "src/$tu.c" -o "/tmp/$tu.o"
        o="$o /tmp/$tu.o"
    done
    gcc -O2 -mfma -Iinclude -c tools/kerneltest.c -o /tmp/kt.o
    gcc -O2 -mfma -o "$out" $o /tmp/kt.o -lm
}

rel_minus() {
    local drop=$1 out="" f
    for f in -ffp-contract=fast -fassociative-math -freciprocal-math -fno-signed-zeros -fno-trapping-math -ffinite-math-only; do
        case "$drop:$f" in
            ffp-contract:-ffp-contract=fast) out="$out -ffp-contract=off";;
            fassociative-math:-fassociative-math) ;;
            freciprocal-math:-freciprocal-math) ;;
            fno-signed-zeros:-fno-signed-zeros) ;;
            ffinite-math-only:-ffinite-math-only) ;;
            *) out="$out $f";;
        esac
    done
    echo "$out"
}

build_one_suppressed() {
    local out=$1 stu=$2 sflag=$3 o="" tu fp
    local sfp; sfp=$(rel_minus "$sflag")
    for tu in geom helpers accum gain guard flux; do
        if [ "$tu" = "$stu" ]; then fp="$sfp"; else fp="$REL"; fi
        gcc -O2 -mfma $fp -Iinclude -c "src/$tu.c" -o "/tmp/$tu.o"
        o="$o /tmp/$tu.o"
    done
    gcc -O2 -mfma -Iinclude -c tools/kerneltest.c -o /tmp/kt.o
    gcc -O2 -mfma -o "$out" $o /tmp/kt.o -lm
}

cat > /tmp/invcheck.c <<'CEOF'
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
static double P(const char *s){ return strtod(s, NULL); }
int main(int c, char **v){
    const char *k = v[1];
    double out = P(v[2]);
    double a0 = c>3?P(v[3]):0, a1 = c>4?P(v[4]):0, a2 = c>5?P(v[5]):0, a3 = c>6?P(v[6]):0;
    const double EPS = 2.220446049250313e-16;
    int hold = 1;
    if (!strcmp(k,"cross2")) { if (a0==a2 && a1==a3) hold = (out==0.0); }
    else if (!strcmp(k,"clamp01")) hold = (!isnan(out) && out>=0.0 && out<=1.0);
    else if (!strcmp(k,"recover")) { if ((a0+a1)==a0) hold = (out==0.0); }
    else if (!strcmp(k,"sign_of")) hold = (out==-1.0||out==0.0||out==1.0);
    else if (!strcmp(k,"cascade")) hold = (out == (a0/a1)/a2);
    else if (!strcmp(k,"roundtrip_residual")) hold = (!isnan(out) && out <= 8*EPS);
    else if (!strcmp(k,"polarity")) { if (a0==a1) hold = (out==-1.0); }
    else if (!strcmp(k,"magdiff")) hold = (!isnan(out) && out>=0.0);
    else if (!strcmp(k,"domain_guard")) hold = !isnan(out);
    else if (!strcmp(k,"horner")) { if (a0>=0.0) hold = (out>=1.0); }
    else { fprintf(stderr,"unknown %s\n", k); return 2; }
    printf(hold ? "HOLD\n" : "VIOLATE\n");
    return 0;
}
CEOF
gcc -O2 -o /tmp/invcheck /tmp/invcheck.c -lm

build_uniform /tmp/kt_strict "$STR"
build_uniform /tmp/kt_release "$REL"

FLAGS="ffp-contract fassociative-math freciprocal-math fno-signed-zeros ffinite-math-only"

# Locate the (TU, flag) that fixes a breaching kernel on its witness.
locate() {
    local kernel=$1 own_tu=$2; shift 2
    local tu flag out v
    for tu in "$own_tu" helpers; do
        for flag in $FLAGS; do
            build_one_suppressed /tmp/kt_fix "$tu" "$flag"
            out=$(/tmp/kt_fix "$kernel" "$@")
            v=$(/tmp/invcheck "$kernel" "$out" "$@")
            if [ "$v" = "HOLD" ]; then
                echo "$tu $flag"
                return 0
            fi
        done
    done
    echo ""
}

# Each entry: kernel own_tu witness-args. Only kernels that actually breach
# under release contribute a suppression pair.
declare -a PAIRS=()
consider() {
    local kernel=$1 own_tu=$2; shift 2
    local r v pair
    r=$(/tmp/kt_release "$kernel" "$@")
    v=$(/tmp/invcheck "$kernel" "$r" "$@")
    [ "$v" = "VIOLATE" ] || return 0
    pair=$(locate "$kernel" "$own_tu" "$@")
    [ -n "$pair" ] && PAIRS+=("$pair")
}

consider cross2 geom 0.1 0.3 0.1 0.3
consider recover accum 1e16 1.0
consider cascade gain 7.0 5.0 3.0
consider polarity flux 1.0 1.0
consider domain_guard guard 0.0 0.0

# Group pairs into tu -> [flags] and emit JSON keyed by source filename.
{
    printf '{\n'
    seen=""
    first=1
    for tu in geom helpers accum gain guard flux; do
        flags=""
        for p in "${PAIRS[@]}"; do
            set -- $p
            if [ "$1" = "$tu" ]; then
                [ -n "$flags" ] && flags="$flags "
                flags="$flags$2"
            fi
        done
        [ -z "$flags" ] && continue
        [ $first -eq 0 ] && printf ',\n'
        first=0
        arr="["; i=0
        for f in $flags; do [ $i -gt 0 ] && arr="$arr, "; arr="$arr\"$f\""; i=1; done
        arr="$arr]"
        printf '  "%s.c": %s' "$tu" "$arr"
    done
    printf '\n}\n'
} > output/result_3.json

cat output/result_3.json
