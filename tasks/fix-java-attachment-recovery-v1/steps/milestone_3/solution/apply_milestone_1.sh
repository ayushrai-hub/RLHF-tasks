#!/bin/bash
set -eo pipefail

cd /app

cat > attachment-core/src/main/java/com/attachment/core/AttachmentConfigLoader.java << 'EOF'
package com.attachment.core;

import java.io.IOException;
import java.io.InputStream;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import java.util.Properties;

public class AttachmentConfigLoader {
    public static AttachmentConfig load(Path configPath) throws IOException {
        Properties properties = new Properties();
        try (InputStream input = Files.newInputStream(configPath)) {
            properties.load(input);
        }

        BigDecimal minimumAttachmentAmount = new BigDecimal(properties.getProperty("minimum.attachment.amount", "0.00"));
        BigDecimal baseAttachmentRate = new BigDecimal(properties.getProperty("base.attachment.rate", "0.00"));
        BigDecimal processingFeeRate = new BigDecimal(properties.getProperty("processing.fee.rate", "0.00"));
        BigDecimal layerCreditRate = new BigDecimal(properties.getProperty("layer.credit.rate", "0.00"));
        BigDecimal trancheHoldbackRate = new BigDecimal(properties.getProperty("tranche.holdback.rate", "0.00"));
        BigDecimal premiumCatastropheCreditRate = new BigDecimal(
                properties.getProperty("attachment.rate.layer.premium", layerCreditRate.toPlainString())
        );
        BigDecimal premiumRetentionHoldbackRate = new BigDecimal(
                properties.getProperty("attachment.rate.holdback.premium", trancheHoldbackRate.toPlainString())
        );
        BigDecimal premiumLossThreshold = new BigDecimal(
                properties.getProperty("attachment.threshold.exposure.premium", "999999.99")
        );
        BigDecimal catastropheThreshold = new BigDecimal(
                properties.getProperty("attachment.threshold.layer", "999999.99")
        );

        Map<String, BigDecimal> adjustmentRates = new HashMap<>();
        for (String key : properties.stringPropertyNames()) {
            if (key.startsWith("adjustment.tier.")) {
                String tier = key.substring("adjustment.tier.".length()).toLowerCase();
                adjustmentRates.put(tier, new BigDecimal(properties.getProperty(key)));
            }
        }

        return new AttachmentConfig(
                minimumAttachmentAmount,
                baseAttachmentRate,
                processingFeeRate,
                layerCreditRate,
                trancheHoldbackRate,
                premiumCatastropheCreditRate,
                premiumRetentionHoldbackRate,
                premiumLossThreshold,
                catastropheThreshold,
                adjustmentRates
        );
    }
}
EOF

cat > attachment-core/src/main/java/com/attachment/core/EligibilityRules.java << 'EOF'
package com.attachment.core;

import java.math.BigDecimal;

public class EligibilityRules {
    public boolean isApproved(Attachment recovery) {
        return "approved".equalsIgnoreCase(recovery.getStatus());
    }

    public boolean hasLossAmount(Attachment recovery) {
        return recovery.getLossAmount().compareTo(BigDecimal.ZERO) > 0;
    }

    public boolean meetsMinimum(Attachment recovery, AttachmentConfig config) {
        return recovery.getLossAmount().compareTo(config.getMinimumAttachmentAmount()) >= 0;
    }
}
EOF
