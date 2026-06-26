# Staging contract

## spectra-ingest-snapshot.json

Written by ingest to /app/state/spectra-ingest-snapshot.json.

| Field | Type | Description |
|-------|------|-------------|
| run_id | string | Manifest run_id |
| profile_fingerprint | string | SHA-256 hex of merged profile per commit-manifest.md |
| samples_used | integer | CSV row count |
| filled_pressures | array | Drift-corrected, gap-filled pressure series in Pa |

## spectra-commit-bind.json

Written by ingest to /app/state/spectra-commit-bind.json.

| Field | Type | Description |
|-------|------|-------------|
| run_id | string | Manifest run_id |
| profile_fingerprint | string | Must match staging snapshot |
| spectral_bind | string | SHA-256 bind digest per commit-manifest.md |

Export reads both artifacts and refuses when bind or fingerprint drift is detected.
