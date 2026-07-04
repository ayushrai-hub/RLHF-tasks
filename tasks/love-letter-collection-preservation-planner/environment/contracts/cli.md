# CLI

heirloom-collection-intake scans .letterfolio artifact descriptors plus collection.json from an archive root (default /app/heirloom-archive) and writes bind artifacts listed in publish-stage.md.

Exit codes:
- 0 on success
- 1 on usage or missing archive root
- 2 on descriptor scan failure

heirloom-preservation-publish reads certified bind artifacts only and writes output files listed in publish-stage.md. Publish must not re-scan letterfolio fragments.

Exit codes:
- 0 on success
- 1 on missing or tampered bind artifacts
- 2 on schedule serialization failure

HEIRLOOM_ARCHIVE_ROOT when set to an absolute path replaces the default archive root and any positional archive argument.
