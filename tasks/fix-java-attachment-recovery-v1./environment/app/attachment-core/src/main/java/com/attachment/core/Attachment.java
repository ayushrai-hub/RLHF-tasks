package com.attachment.core;

import java.math.BigDecimal;

public class Attachment {
    private final String id;
    private final String obligor;
    private final BigDecimal exposureAmount;
    private final String status;
    private final String programTier;

    public Attachment(String id, String obligor, BigDecimal exposureAmount, String status, String programTier) {
        this.id = id;
        this.obligor = obligor;
        this.exposureAmount = exposureAmount;
        this.status = status;
        this.programTier = programTier;
    }

    public String getId() { return id; }
    public String getCedent() { return obligor; }
    public BigDecimal getLossAmount() { return exposureAmount; }
    public String getStatus() { return status; }
    public String getTreatyTier() { return programTier; }
}
