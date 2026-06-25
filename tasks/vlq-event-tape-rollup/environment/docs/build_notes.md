CMake plus Ninja build under `/app/environment` produces `/app/build/vlt_run`.

Typical cold flow:

```
cmake -S /app/environment -B /app/build -G Ninja
ninja -C /app/build
/app/build/vlt_run /app/environment/fixtures/z7bind.json /app/output/vlt_report.json --reset
```

Warm replay reuses lane entries when bundle fingerprints match:

```
/app/build/vlt_run /app/environment/fixtures/z7bind.json /app/output/vlt_report.json --warm
```

The verifier re-runs the Ninja configure sequence; do not switch generators.
