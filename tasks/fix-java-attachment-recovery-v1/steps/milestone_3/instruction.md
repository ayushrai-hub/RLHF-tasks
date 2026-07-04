Keep the pipeline order and tier adjustment basis from the prior step intact. Update layer credit calculation, tier adjustment rounding, and tranche holdback logic in the attachment-engine module only.

Layer credit must be computed on base attachment, not raw exposure amount. Premium layer and holdback rates apply from exposure amount thresholds in `/app/docs/config-keys.md`, not program tier alone. Apply HALF_DOWN rounding exceptions from `/app/docs/rounding-schedule.md`. Tranche holdback taxable base must include `processingFeeAmount` per `/app/docs/tranche-holdback-addendum.md`.

After updating attachment-engine logic, regenerate the report from /app with `mvn -q -B -o install -DskipTests` followed by `mvn -q -B -o -pl attachment-batch exec:java` and confirm rounding-sensitive attachments such as ATT-028 and ATT-031 match the docs.
