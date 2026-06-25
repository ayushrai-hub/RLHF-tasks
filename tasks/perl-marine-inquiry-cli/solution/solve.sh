#!/bin/bash
set -uo pipefail

# Harness mounts solution sources at /oracle for oracle-agent runs and at
# /solution for interactive start-env runs. Probe both.
SOLUTION_DIR=""
for cand in /oracle /solution; do
    if [ -f "$cand/src/inquire.pl" ]; then
        SOLUTION_DIR="$cand"
        break
    fi
done

if [ -z "$SOLUTION_DIR" ]; then
    echo "solve: no inquire.pl found at /oracle/src or /solution/src" >&2
    exit 1
fi
echo "solve: using SOLUTION_DIR=$SOLUTION_DIR" >&2

test -f /app/api/db/case.sqlite3 || {
    echo "solve: missing /app/api/db/case.sqlite3 (image build did not seed)" >&2
    exit 1
}
command -v perl >/dev/null || { echo "solve: perl missing on PATH" >&2; exit 1; }

mkdir -p /app/build /app/output /app/state
rm -rf /app/output/* /app/state/*

cp "$SOLUTION_DIR/src/inquire.pl" /app/build/inquire.pl
cp "$SOLUTION_DIR/src/inquire.sh" /app/build/inquire.sh
chmod +x /app/build/inquire.sh

# In the agent environment no sealed solution is loaded, so both runs report a
# "pending" verdict; the finding is adjudicated at submission review, when the
# verifier injects the sealed conclusion and re-runs the play.
/app/build/inquire.sh play
/app/build/inquire.sh wrong

ls -la /app/output
