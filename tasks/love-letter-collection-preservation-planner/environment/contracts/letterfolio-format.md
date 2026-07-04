# Letterfolio format

Each .letterfolio file contains one artifact record with lines:
ARTIFACT id
KEEPSAKE box-name
MEDIA_SLOT signed-integer-offset-hours (sign preserved on ingest)
ERA primary-era-tag
FORMAT general-or-specific-tag
When a letterfolio omits FORMAT, ingest must treat the artifact format tag as general for migration-rollup grouping.
REDUNDANCY integer
Optional FRAGILE space-or-comma-separated artifact ids
Optional CROSSREF space-or-comma-separated prior pairing partners (sorted on ingest)
Optional BYTES integer storage weight

Lines use KEYWORD value form (space-separated), not key=value pairs.
