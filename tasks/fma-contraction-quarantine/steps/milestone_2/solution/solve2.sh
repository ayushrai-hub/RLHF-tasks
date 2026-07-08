#!/usr/bin/env bash
# Milestone 2 oracle: build strict and release, then for each kernel probe its
# documented invariant. A kernel is a hazard iff the release build crosses the
# invariant on a structured input while the strict build holds it.
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

# Invariant decider: prints HOLD or VIOLATE for a kernel output given its inputs.
# Compiled without fast-math so its own comparisons stay exact.
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

invariant_id() {
    case "$1" in
        cross2) echo self_cross_zero;;
        recover) echo absorbed_zero;;
        cascade) echo staged_quotient;;
        polarity) echo equal_negative;;
        domain_guard) echo never_nan;;
        *) echo "";;
    esac
}

json_array() {
    local out="[" i=0 x
    for x in "$@"; do [ $i -gt 0 ] && out="$out, "; out="$out$x"; i=1; done
    echo "$out]"
}

emit() {
    local k=$1; shift
    local s r vs vr
    s=$(/tmp/kt_strict "$k" "$@")
    r=$(/tmp/kt_release "$k" "$@")
    vs=$(/tmp/invcheck "$k" "$s" "$@")
    vr=$(/tmp/invcheck "$k" "$r" "$@")
    [ $FIRST -eq 0 ] && printf ',\n'
    FIRST=0
    if [ "$vs" = "HOLD" ] && [ "$vr" = "VIOLATE" ]; then
        printf '  "%s": {"verdict": "HAZARD", "witness": %s, "invariant": "%s"}' \
            "$k" "$(json_array "$@")" "$(invariant_id "$k")"
    else
        printf '  "%s": {"verdict": "BENIGN"}' "$k"
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
} > output/result_2.json

cat output/result_2.json
