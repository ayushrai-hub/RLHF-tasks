Example:

```bash
cmake -S /app -B /app/build
cmake --build /app/build
/app/build/pc-sanitize audit --pc-dir /app/input/pkgconfig --manifest /app/input/manifests/release.json --out /tmp/audit.json
```

The checked fixtures model a common release issue: a library exposes static-only flags in public pkg-config metadata, and another package links a library directly instead of declaring the dependency edge that would let pkg-config resolve it.
