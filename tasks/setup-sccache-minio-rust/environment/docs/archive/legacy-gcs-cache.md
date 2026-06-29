# Archived: GCS compile cache (pre-MinIO migration)

Meridian CI previously published Rust build artifacts to a Google Cloud Storage bucket via `SCCACHE_GCS_BUCKET` and application-default credentials. That backend was retired when on-host MinIO replaced GCS for offline build hosts.

Do not configure new workspaces against this document.
