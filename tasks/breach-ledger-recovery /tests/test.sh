#!/bin/bash

if [ "$PWD" = "/" ]; then
  echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile."
  exit 1
fi

mkdir -p /logs/verifier

set +e
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
first=$?
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
second=$?

if [ $first -eq 0 ] && [ $second -eq 0 ]; then
  true
else
  false
fi
status=$?
if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
