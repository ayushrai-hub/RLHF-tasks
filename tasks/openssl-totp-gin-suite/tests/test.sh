#!/bin/bash

# Verifier Python/pytest are baked in the image (see environment/Dockerfile).

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile."
    exit 1
fi

mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
verify_rc=$?

if [ "$verify_rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
