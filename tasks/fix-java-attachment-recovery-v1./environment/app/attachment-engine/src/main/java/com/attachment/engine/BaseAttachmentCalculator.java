package com.attachment.engine;

import com.attachment.core.Attachment;
import com.attachment.core.AttachmentConfig;

import java.math.BigDecimal;
import java.math.RoundingMode;

public class BaseAttachmentCalculator {
    public BigDecimal baseAttachment(Attachment recovery, AttachmentConfig config) {
        return recovery.getLossAmount()
                .multiply(config.getBaseAttachmentRate())
                .setScale(2, RoundingMode.HALF_UP);
    }
}
