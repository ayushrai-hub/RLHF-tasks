# Manifest catalog

Bundled manifests under `/app/fixtures/manifests/`:

- `storm-alpha.json` — primary regression window
- `storm-beta.json` — includes decoy `sample_rate_hz` manifest hint (must be ignored)

Hidden probes install to `/opt/verifier-fixtures/buoy-spectra-probes/` at image build.

Fetch example:

```text
curl -fsSL file:///app/fixtures/manifests/storm-alpha.json
```
