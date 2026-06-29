package com.attachment.engine;

import com.attachment.core.Attachment;
import com.attachment.core.AttachmentConfig;

import java.math.BigDecimal;

public final class LayerBasisRules {
    private LayerBasisRules() {
    }

    public static BigDecimal tierPremiumBasis(
            Attachment recovery,
            BigDecimal baseAttachment,
            BigDecimal layerCreditAmount,
            AttachmentConfig config
    ) {
        if (recovery.getLossAmount().compareTo(config.getCatastropheThreshold()) > 0) {
            return baseAttachment.subtract(layerCreditAmount);
        }
        return baseAttachment;
    }
}
