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

        BigDecimal taxable = baseAttachment.subtract(tierAdjustmentAmount).subtract(layerCreditAmount);
        BigDecimal rate = PremiumRetentionHoldbackPolicy.trancheHoldbackRate(
                recovery.getLossAmount(),
                config.getPremiumLossThreshold(),
                config.getRetentionHoldbackRate(),
                config.getPremiumRetentionHoldbackRate()
        );
        if ("premium".equalsIgnoreCase(recovery.getTreatyTier())) {
            rate = config.getPremiumRetentionHoldbackRate();
        }
        return taxable.multiply(rate).setScale(2, RoundingMode.HALF_DOWN);
    }
}
