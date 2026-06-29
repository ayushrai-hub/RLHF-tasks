Implement the wcs-atlas FITS World Coordinate System CLI on the working /app baseline. Add FITS header ingestion, keyword staging, linear WCS matrix assembly, TAN and SIN spatial projection evaluation, and sky atlas export so build satisfies the contracts in /app/docs. Keyword snapshot canonical strings and corner ordering must be deterministic across repeated builds.

Wire wcs-atlas at /app/bin/wcs-atlas per /app/docs/cli-surface.md. The build subcommand accepts an absolute or relative path to a FITS file, parses the primary HDU header, writes /app/var/wcs-keyword-snapshot.json per /app/docs/keyword-snapshot-schema.md, and writes /app/output/wcs-atlas.json per /app/docs/atlas-schema.md including corner and axis-midpoint RA and Dec in degrees, projection family, pixel scales, and a fingerprint field.

FITS card continuation and HIERARCH rules are in /app/docs/fits-header-lexer.md. CD versus PC matrix composition is in /app/docs/wcs-linear-transform.md. TAN and SIN projection formulas are in /app/docs/projection-models.md. CRPIX is 1-based per /app/docs/pixel-conventions.md. Default paths are in /app/config/wcs-atlas.toml.

When TB3_FITS_PATH is set to an absolute path to a FITS file, build must use that file instead of the positional path argument per /app/docs/cli-surface.md. Rebuild with /app/scripts/build.sh after editing sources under /app/src.

Repeated build on unchanged FITS input must yield byte-identical /app/output/wcs-atlas.json and /app/var/wcs-keyword-snapshot.json.
