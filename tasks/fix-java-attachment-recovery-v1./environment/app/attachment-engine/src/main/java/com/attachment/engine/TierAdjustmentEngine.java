package com.attachment.engine;

import com.attachment.core.Attachment;
import com.attachment.core.AttachmentConfig;

import java.math.BigDecimal;
import java.math.RoundingMode;

public class TierAdjustmentEngine {
    public BigDecimal adjustmentRate(Attachment recovery, AttachmentConfig config) {
        return config.getAdjustmentRate(recovery.getTreatyTier());
    }

    public BigDecimal tierAdjustmentAmount(Attachment recovery, BigDecimal baseAttachment, AttachmentConfig config) {
        BigDecimal rate = adjustmentRate(recovery, config);
        BigDecimal basis = baseAttachment;
        if (recovery.getLossAmount().compareTo(config.getCatastropheThreshold()) > 0) {
            if ("plus".equalsIgnoreCase(recovery.getTreatyTier())) {
                basis = recovery.getLossAmount();
            }
        }
        return basis.multiply(rate).setScale(2, RoundingMode.HALF_UP);
    }
}
