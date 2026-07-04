#!/bin/bash
mkdir -p /logs/verifier

if [ ! -d /app/environment ]; then
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

STATUS=0
ANALYSIS=/app/environment/analysis.R
DATA_DIR=/app/environment/data/states
OUT_DIR=/app/environment/outputs
BACKUP_DIR=/tmp/incarceration_public_backup

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"
Rscript "$ANALYSIS"
rc=$?
[ $rc -ne 0 ] && STATUS=1

if [ $STATUS -eq 0 ]; then
    python3 -m pytest /tests/test_outputs.py -rA -q -p no:cacheprovider \
        --ctrf /logs/verifier/ctrf-report.json
    rc=$?
    [ $rc -ne 0 ] && STATUS=1
fi

if [ $STATUS -eq 0 ]; then
    rm -rf "$BACKUP_DIR"
    cp -r "$DATA_DIR" "$BACKUP_DIR"
    python3 /tests/generate_hidden_data.py
    rc=$?
    [ $rc -ne 0 ] && STATUS=1
fi

if [ $STATUS -eq 0 ]; then
    rm -rf "$OUT_DIR"
    mkdir -p "$OUT_DIR"
    Rscript "$ANALYSIS"
    rc=$?
    [ $rc -ne 0 ] && STATUS=1
fi

if [ $STATUS -eq 0 ]; then
    HIDDEN_VARIANT=1 python3 -m pytest /tests/test_outputs.py -rA -q -p no:cacheprovider \
        --ctrf /logs/verifier/ctrf-report-hidden.json
    rc=$?
    [ $rc -ne 0 ] && STATUS=1
fi

if [ -d "$BACKUP_DIR" ]; then
    rm -rf "$DATA_DIR"
    cp -r "$BACKUP_DIR" "$DATA_DIR"
fi

[ $STATUS -eq 0 ]
if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
