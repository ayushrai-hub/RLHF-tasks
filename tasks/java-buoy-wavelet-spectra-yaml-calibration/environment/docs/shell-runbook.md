# Shell runbook

Pipeline entry:

```text
/app/scripts/run-spectra-pipeline.sh --manifest <abs.json> --output <abs-report.json>
```

Manifest fetch helper (offline `file://` only):

```text
/app/scripts/fetch-manifest.sh file:///app/fixtures/manifests/storm-alpha.json
```

Rebuild Java after edits:

```text
cd /app && mvn -q clean -DskipTests package
```
