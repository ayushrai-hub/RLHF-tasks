# wcs-atlas CLI

Commands:

- wcs-atlas build FITS_PATH — parse primary HDU header, write keyword snapshot and sky atlas JSON

FITS_PATH may be absolute or relative to the current working directory.

Environment override TB3_FITS_PATH: when set to an absolute path to a FITS file, build uses that file instead of the positional FITS_PATH argument.

Rebuild after source edits: /app/scripts/build.sh (also available as rebuild-wcs-atlas on PATH in the verifier).

Default output paths from /app/config/wcs-atlas.toml.

Every successful build writes /app/var/wcs-ingest-stamp.txt containing the resolved FITS path used for ingest (one line). The stamp is written only after the primary HDU header is read successfully.

When FITS_PATH or the TB3_FITS_PATH override names a file that does not exist or cannot be opened, build exits with a non-zero status and must not write atlas or snapshot outputs. Verifier negative tests use paths such as /app/output/no-such-file.fits for this case.
