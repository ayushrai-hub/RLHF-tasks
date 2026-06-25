"""Benchmark for sliding window rate limiter."""
import subprocess
import json
import sys

def main():
    r = subprocess.run(["/app/bin/rate-limiter", "analyze",
        "--traffic", "/app/data/traffic", "--output", "/tmp/bench", "--format", "json"],
        capture_output=True, timeout=30)
    if r.returncode != 0:
        print(f"FAIL: {r.returncode}")
        sys.exit(1)
    with open("/tmp/bench/limiter_report.json") as f:
        report = json.load(f)
    print(f"Requests: {report['total_requests']}, Denied: {report['denied_count']}")

if __name__ == "__main__":
    main()
