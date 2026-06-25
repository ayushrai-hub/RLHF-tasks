#!/usr/bin/env python3
"""Regenerate data/manifest.json from the cases under data/cases/.

Dev utility. Runs the built cronq.jar against each case and writes the
reference fire times back into the manifest. Only the cases listed in
SUBSET end up in the manifest; the rest stay reference-only in the tests.

    python3 tools/gen_manifest.py
"""
import json
import os
import subprocess
import sys

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JAR = os.path.join(APP, "cronq.jar")
CASES = os.path.join(APP, "data", "cases")
MANIFEST = os.path.join(APP, "data", "manifest.json")

# Only these cases are published in the manifest.
SUBSET = [
    "c1_daily_midnight",
    "c3_quarter_hour_offset",
    "c6_friday_thirteenth",
    "c8_march_noon",
    "c9_leap_day",
]


def run_case(case):
    r = subprocess.run(
        ["java", "-jar", JAR, "next",
         "--expr", case["expr"],
         "--from", case["from"],
         "--count", str(case["count"])],
        capture_output=True, text=True, check=True,
    )
    return json.loads(r.stdout)["matches"]


def main():
    ref = {}
    for name in SUBSET:
        with open(os.path.join(CASES, name + ".json")) as f:
            case = json.load(f)
        ref[name] = run_case(case)

    out = {
        "_comment": ("Reference fire times for a subset of the cases under "
                     "data/cases/. Computed from the protocol, not from the "
                     "current build. The CLI output for each listed case must "
                     "match exactly."),
        "reference": ref,
    }
    with open(MANIFEST, "w") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    print("wrote", MANIFEST, file=sys.stderr)


if __name__ == "__main__":
    main()
