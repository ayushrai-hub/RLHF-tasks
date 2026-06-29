package com.attachment.engine;

import com.attachment.core.Attachment;
import com.attachment.core.AttachmentConfig;

import java.math.BigDecimal;
import java.math.RoundingMode;

public class LayerCreditEngine {
    public BigDecimal layerCreditAmount(Attachment recovery, BigDecimal baseAttachment, AttachmentConfig config) {
        if (recovery.getLossAmount().compareTo(config.getCatastropheThreshold()) > 0) {
            BigDecimal rate = config.getCatastropheCreditRate();
            if ("premium".equalsIgnoreCase(recovery.getTreatyTier())
                    && recovery.getLossAmount().compareTo(config.getPremiumLossThreshold()) >= 0) {
                rate = config.getPremiumCatastropheCreditRate();
            }
            return recovery.getLossAmount().multiply(rate).setScale(2, RoundingMode.HALF_UP);
        }
        return BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP);
    }
}
