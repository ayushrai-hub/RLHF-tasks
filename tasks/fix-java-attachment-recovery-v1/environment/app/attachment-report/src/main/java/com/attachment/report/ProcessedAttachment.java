package com.attachment.report;

import java.math.BigDecimal;

public class ProcessedAttachment {
    private final String id;
    private final String obligor;
    private final BigDecimal exposureAmount;
    private final String programTier;
    private final BigDecimal baseAttachment;
    private final BigDecimal processingFeeAmount;
    private final BigDecimal adjustmentRate;
    private final BigDecimal tierAdjustmentAmount;
    private final BigDecimal layerCreditAmount;
    private final BigDecimal trancheHoldbackAmount;
    private final BigDecimal netAttachment;

    public ProcessedAttachment(String id, String obligor, BigDecimal exposureAmount, String programTier,
            BigDecimal baseAttachment, BigDecimal processingFeeAmount, BigDecimal adjustmentRate,
            BigDecimal tierAdjustmentAmount, BigDecimal layerCreditAmount,
            BigDecimal trancheHoldbackAmount, BigDecimal netAttachment) {
        this.id = id;
        this.obligor = obligor;
        this.exposureAmount = exposureAmount;
        this.programTier = programTier;
        this.baseAttachment = baseAttachment;
        this.processingFeeAmount = processingFeeAmount;
        this.adjustmentRate = adjustmentRate;
        this.tierAdjustmentAmount = tierAdjustmentAmount;
        this.layerCreditAmount = layerCreditAmount;
        this.trancheHoldbackAmount = trancheHoldbackAmount;
        this.netAttachment = netAttachment;
    }

    public String getId() { return id; }
    public String getCedent() { return obligor; }
    public BigDecimal getLossAmount() { return exposureAmount; }
    public String getTreatyTier() { return programTier; }
    public BigDecimal getBaseAttachment() { return baseAttachment; }
    public BigDecimal getProcessingFeeAmount() { return processingFeeAmount; }
    public BigDecimal getAdjustmentRate() { return adjustmentRate; }
    public BigDecimal getTierAdjustmentAmount() { return tierAdjustmentAmount; }
    public BigDecimal getCatastropheCreditAmount() { return layerCreditAmount; }
    public BigDecimal getRetentionHoldbackAmount() { return trancheHoldbackAmount; }
    public BigDecimal getNetAttachment() { return netAttachment; }
}
