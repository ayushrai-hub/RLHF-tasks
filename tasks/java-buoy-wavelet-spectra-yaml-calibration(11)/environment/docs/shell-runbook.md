# Shell runbook

Full pipeline:

```text
/app/scripts/run-spectra-pipeline.sh --manifest <abs.json> --output <abs-report.json>
```

Jar subcommands:

```text
java -jar /app/target/buoy-spectra-jar-with-dependencies.jar ingest --manifest <abs.json>
java -jar /app/target/buoy-spectra-jar-with-dependencies.jar export --manifest <abs.json> --output <abs-report.json>
java -jar /app/target/buoy-spectra-jar-with-dependencies.jar process --manifest <abs.json> --output <abs-report.json>
```

Manifest fetch helper (offline file:// only):

```text
/app/scripts/fetch-manifest.sh file:///app/fixtures/manifests/storm-alpha.json
```

Rebuild Java after edits:

```text
cd /app && mvn -q clean -DskipTests package
```
