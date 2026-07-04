#!/bin/bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd /app

ls docs/
head -n 90 docs/pricing-policy.md
grep -nE 'Gson|pretty|netAttachment|layerCredit|sort|generatedAt|attachments|summary|adjustmentRate' \
    docs/pricing-policy.md docs/layer-addendum.md docs/tranche-holdback-addendum.md docs/rounding-schedule.md docs/config-keys.md

grep -nE 'override|minimum\.|adjustment\.tier|layer\.credit' \
    attachment-core/src/main/java/com/attachment/core/AttachmentConfigLoader.java || true
grep -nE 'approved|meetsMinimum|equalsIgnoreCase' \
    attachment-core/src/main/java/com/attachment/core/EligibilityRules.java || true
grep -nE 'sort|tierAdjustment|layerCredit|netAttachment' \
    attachment-engine/src/main/java/com/attachment/engine/AttachmentProcessor.java \
    attachment-engine/src/main/java/com/attachment/engine/TierAdjustmentEngine.java \
    attachment-engine/src/main/java/com/attachment/engine/LayerCreditEngine.java || true
grep -nE 'Gson|generatedAt|processingFee|totalAttachment|PremiumRetention' \
    attachment-report/src/main/java/com/attachment/report/ReportGenerator.java \
    attachment-report/src/main/java/com/attachment/report/FinancePolicy.java \
    attachment-engine/src/main/java/com/attachment/engine/TrancheHoldbackCalculator.java || true

mvn -q -B -o test
if test -f output/attachment-report.json; then
  head -n 25 output/attachment-report.json
fi

bash "${SCRIPT_DIR}/apply_milestone_1.sh"
mvn -q -B -o test
