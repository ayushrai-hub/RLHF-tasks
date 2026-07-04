package com.attachment.core;

import java.math.BigDecimal;
import java.util.Map;

public class AttachmentConfig {
    private final BigDecimal minimumAttachmentAmount;
    private final BigDecimal baseAttachmentRate;
    private final BigDecimal processingFeeRate;
    private final BigDecimal layerCreditRate;
    private final BigDecimal trancheHoldbackRate;
    private final BigDecimal premiumCatastropheCreditRate;
    private final BigDecimal premiumRetentionHoldbackRate;
    private final BigDecimal premiumLossThreshold;
    private final BigDecimal catastropheThreshold;
    private final Map<String, BigDecimal> adjustmentRates;

    public AttachmentConfig(BigDecimal minimumAttachmentAmount, BigDecimal baseAttachmentRate,
            BigDecimal processingFeeRate, BigDecimal layerCreditRate,
            BigDecimal trancheHoldbackRate, BigDecimal premiumCatastropheCreditRate,
            BigDecimal premiumRetentionHoldbackRate, BigDecimal premiumLossThreshold,
            BigDecimal catastropheThreshold, Map<String, BigDecimal> adjustmentRates) {
        this.minimumAttachmentAmount = minimumAttachmentAmount;
        this.baseAttachmentRate = baseAttachmentRate;
        this.processingFeeRate = processingFeeRate;
        this.layerCreditRate = layerCreditRate;
        this.trancheHoldbackRate = trancheHoldbackRate;
        this.premiumCatastropheCreditRate = premiumCatastropheCreditRate;
        this.premiumRetentionHoldbackRate = premiumRetentionHoldbackRate;
        this.premiumLossThreshold = premiumLossThreshold;
        this.catastropheThreshold = catastropheThreshold;
        this.adjustmentRates = adjustmentRates;
    }

    public BigDecimal getMinimumAttachmentAmount() { return minimumAttachmentAmount; }
    public BigDecimal getBaseAttachmentRate() { return baseAttachmentRate; }
    public BigDecimal getProcessingFeeRate() { return processingFeeRate; }
    public BigDecimal getCatastropheCreditRate() { return layerCreditRate; }
    public BigDecimal getRetentionHoldbackRate() { return trancheHoldbackRate; }
    public BigDecimal getPremiumCatastropheCreditRate() { return premiumCatastropheCreditRate; }
    public BigDecimal getPremiumRetentionHoldbackRate() { return premiumRetentionHoldbackRate; }
    public BigDecimal getPremiumLossThreshold() { return premiumLossThreshold; }
    public BigDecimal getCatastropheThreshold() { return catastropheThreshold; }

    public BigDecimal getAdjustmentRate(String programTier) {
        if (programTier == null) return BigDecimal.ZERO;
        BigDecimal rate = adjustmentRates.get(programTier.toUpperCase());
        if (rate == null) rate = adjustmentRates.get(programTier.toLowerCase());
        return rate != null ? rate : BigDecimal.ZERO;
    }
}
