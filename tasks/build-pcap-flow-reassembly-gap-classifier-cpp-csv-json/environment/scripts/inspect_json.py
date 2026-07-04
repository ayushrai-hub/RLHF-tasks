#!/usr/bin/env python3
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)

print(f"streams={payload['totals']['streams']} segments={payload['totals']['segments']} gaps={payload['totals']['gaps']}")
