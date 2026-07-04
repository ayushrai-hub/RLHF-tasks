#!/bin/bash
set -eo pipefail

cd /app

cat > attachment-engine/src/main/java/com/attachment/engine/TierAdjustmentEngine.java << 'EOF'
package com.attachment.engine;

import com.attachment.core.Attachment;
import com.attachment.core.AttachmentConfig;

import java.math.BigDecimal;
import java.math.RoundingMode;

public class TierAdjustmentEngine {
    public BigDecimal adjustmentRate(Attachment recovery, AttachmentConfig config) {
        return config.getAdjustmentRate(recovery.getTreatyTier());
    }

    public BigDecimal tierAdjustmentAmount(
            Attachment recovery,
            BigDecimal baseAttachment,
            BigDecimal layerCreditAmount,
            AttachmentConfig config
    ) {
        BigDecimal rate = adjustmentRate(recovery, config);
        BigDecimal basis = baseAttachment;
        if (("premium".equalsIgnoreCase(recovery.getTreatyTier()) || "plus".equalsIgnoreCase(recovery.getTreatyTier()))
                && recovery.getLossAmount().compareTo(config.getCatastropheThreshold()) >= 0) {
            basis = baseAttachment.subtract(layerCreditAmount);
        }
        BigDecimal rawBonus = basis.multiply(rate);
        if ("plus".equalsIgnoreCase(recovery.getTreatyTier())
                && recovery.getLossAmount().compareTo(config.getCatastropheThreshold()) >= 0) {
            return rawBonus.setScale(2, RoundingMode.HALF_DOWN);
        }
        if ("premium".equalsIgnoreCase(recovery.getTreatyTier())
                && recovery.getLossAmount().compareTo(config.getPremiumLossThreshold()) >= 0) {
            return rawBonus.setScale(2, RoundingMode.HALF_DOWN);
        }
        return rawBonus.setScale(2, RoundingMode.HALF_UP);
    }
}
EOF

cat > attachment-engine/src/main/java/com/attachment/engine/LayerCreditEngine.java << 'EOF'
package com.attachment.engine;

import com.attachment.core.Attachment;
import com.attachment.core.AttachmentConfig;

import java.math.BigDecimal;
import java.math.RoundingMode;

public class LayerCreditEngine {
    public BigDecimal layerCreditAmount(Attachment recovery, BigDecimal baseAttachment, AttachmentConfig config) {
        if (recovery.getLossAmount().compareTo(config.getCatastropheThreshold()) >= 0) {
            BigDecimal rate = config.getCatastropheCreditRate();
            if (recovery.getLossAmount().compareTo(config.getPremiumLossThreshold()) >= 0) {
                rate = config.getPremiumCatastropheCreditRate();
            }
            BigDecimal rawMega = baseAttachment.multiply(rate);
            if ("premium".equalsIgnoreCase(recovery.getTreatyTier())) {
                return rawMega.setScale(2, RoundingMode.HALF_DOWN);
            }
            return rawMega.setScale(2, RoundingMode.HALF_UP);
        }
        return BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP);
    }
}
EOF

cat > attachment-engine/src/main/java/com/attachment/engine/TrancheHoldbackCalculator.java << 'EOF'
package com.attachment.engine;

import com.attachment.core.Attachment;
import com.attachment.core.AttachmentConfig;

import java.math.BigDecimal;
import java.math.RoundingMode;

public class TrancheHoldbackCalculator {
    public BigDecimal trancheHoldbackAmount(
            Attachment recovery,
            BigDecimal baseAttachment,
            BigDecimal tierAdjustmentAmount,
            BigDecimal layerCreditAmount,
            BigDecimal processingFeeAmount,
            AttachmentConfig config
    ) {
        if ("basic".equalsIgnoreCase(recovery.getTreatyTier())
                && recovery.getLossAmount().compareTo(config.getMinimumAttachmentAmount()) == 0) {
            return BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP);
        }

        BigDecimal taxable = baseAttachment
                .subtract(tierAdjustmentAmount)
                .subtract(layerCreditAmount)
                .add(processingFeeAmount);
        BigDecimal rate = config.getRetentionHoldbackRate();
        if (recovery.getLossAmount().compareTo(config.getPremiumLossThreshold()) >= 0) {
            rate = config.getPremiumRetentionHoldbackRate();
        }
        BigDecimal rawHoldback = taxable.multiply(rate);
        if (recovery.getLossAmount().compareTo(config.getCatastropheThreshold()) >= 0) {
            return rawHoldback.setScale(2, RoundingMode.HALF_DOWN);
        }
        return rawHoldback.setScale(2, RoundingMode.HALF_UP);
    }
}
EOF
