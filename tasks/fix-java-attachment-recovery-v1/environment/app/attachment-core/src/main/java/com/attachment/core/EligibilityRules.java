package com.attachment.core;

import java.math.BigDecimal;

public class EligibilityRules {
    public boolean isApproved(Attachment recovery) {
        return "approved".equals(recovery.getStatus());
    }

    public boolean hasLossAmount(Attachment recovery) {
        return recovery.getLossAmount().compareTo(BigDecimal.ZERO) > 0;
    }

    public boolean meetsMinimum(Attachment recovery, AttachmentConfig config) {
        return recovery.getLossAmount().compareTo(config.getMinimumAttachmentAmount()) > 0;
    }
}
