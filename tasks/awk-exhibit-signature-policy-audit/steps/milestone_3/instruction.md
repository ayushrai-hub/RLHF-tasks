Last stage: `/app/bin/audit.sh report` writes /app/output/remediation_report.json. Turn the catalog and the signature evidence into the per-image and per-key remediation actions defined in /app/docs/signing_policy.md, matching /app/config/schemas/remediation_report.schema.json.

The classification logic in /app/lib/media_sig_audit.awk is wrong, which is why good images end up rejected while a stale key keeps its trust. The curators act on this report, so the actions and the summary counts have to come out right.
