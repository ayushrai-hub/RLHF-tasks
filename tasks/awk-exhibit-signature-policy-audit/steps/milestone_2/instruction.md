With the catalog stage producing /app/output/signing_catalog.json, move on to signature evidence. `/app/bin/audit.sh verify` should write /app/output/signature_evidence.json: for every image in the catalog, confirm the signing key's identity and establish whether its detached signature is trustworthy with OpenSSL, the way /app/docs/signing_policy.md defines it and matching /app/config/schemas/signature_evidence.schema.json.

The OpenSSL handling in /app/lib/media_sig_audit.awk is incomplete, so right now the signatures are not all being checked the way the policy requires.
