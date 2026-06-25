#!/bin/bash

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script."
    mkdir -p /logs/verifier
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

mkdir -p /logs/verifier
STATUS=0

rm -rf /app/environment/outputs && mkdir -p /app/environment/outputs
Rscript /app/environment/analysis.R; rc=$?; [ $rc -ne 0 ] && STATUS=1

if [ $STATUS -eq 0 ]; then
  /opt/verifier-venv/bin/pytest -rA /tests/test_outputs.py; rc=$?; [ $rc -ne 0 ] && STATUS=1
fi

if [ $STATUS -eq 0 ]; then
  cp /app/environment/data/BEPS.csv /tmp/beps_public.csv || STATUS=1
fi

if [ $STATUS -eq 0 ]; then
  /opt/verifier-venv/bin/python /tests/generate_hidden_data.py; rc=$?; [ $rc -ne 0 ] && STATUS=1
fi

if [ $STATUS -eq 0 ]; then
  rm -rf /app/environment/outputs && mkdir -p /app/environment/outputs
  Rscript /app/environment/analysis.R; rc=$?; [ $rc -ne 0 ] && STATUS=1
fi

if [ $STATUS -eq 0 ]; then
  HIDDEN_VARIANT=1 /opt/verifier-venv/bin/pytest -rA /tests/test_outputs.py; rc=$?; [ $rc -ne 0 ] && STATUS=1
fi

if [ -f /tmp/beps_public.csv ]; then
  cp /tmp/beps_public.csv /app/environment/data/BEPS.csv || true
fi

[ $STATUS -eq 0 ]
if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
