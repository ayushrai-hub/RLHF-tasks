#!/usr/bin/env bash
source "$HOME/.local/bin/env" 2>/dev/null || true

mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

if [ "$PWD" = "/" ]; then echo "Error: No WORKDIR set in Dockerfile."; exit 1; fi

cd /app

# Rebuild the agent's depmap tool from source so the test exercises their code.
rm -f /usr/local/bin/depmap
CGO_ENABLED=0 go build -o /usr/local/bin/depmap . 2>&1 || true

python3 -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA -v
rc=$?
if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
