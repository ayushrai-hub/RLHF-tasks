#!/usr/bin/env bash
# verify_sig.sh <file> <sigfile>
#
# Offline detached-signature check for the r2 baseline snapshot. Recomputes a
# keyed SHA-256 over <file> using the locally provisioned authority key and
# compares it against the hex value in <sigfile>. Exits 0 on a match and
# non-zero otherwise. Uses coreutils only (no network, no external crypto CLI).
set -u

f="${1:?usage: verify_sig.sh <file> <sigfile>}"
s="${2:?usage: verify_sig.sh <file> <sigfile>}"

# Authority verification key provisioned into the airgapped verifier image.
KEY="airgap-authority-key-v1"

have="$({ printf '%s' "$KEY"; cat "$f"; } | sha256sum | awk '{print $1}')"
want="$(tr -d ' \t\r\n' < "$s")"

[ -n "$have" ] && [ "$have" = "$want" ]
