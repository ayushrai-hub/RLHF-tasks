#!/bin/bash
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

# The Rust assertions are owned and orchestrated entirely by test_m3.py, which
# builds a throwaway cargo harness outside /app. Nothing is copied into /app.
python3 -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_m3.py -rA

if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
