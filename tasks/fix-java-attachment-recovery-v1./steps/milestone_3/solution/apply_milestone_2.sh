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
        return basis.multiply(rate).setScale(2, RoundingMode.HALF_UP);
    }
}
EOF

cat > attachment-engine/src/main/java/com/attachment/engine/AttachmentProcessor.java << 'EOF'
package com.attachment.engine;

import com.attachment.core.EligibilityRules;
import com.attachment.core.Attachment;
import com.attachment.core.AttachmentConfig;
import com.attachment.report.FinancePolicy;
import com.attachment.report.ProcessedAttachment;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

public class AttachmentProcessor {
    private final AttachmentConfig config;
    private final BaseAttachmentCalculator baseAttachmentCalculator = new BaseAttachmentCalculator();
    private final ProcessingFeeCalculator processingFeeCalculator = new ProcessingFeeCalculator();
    private final TierAdjustmentEngine tierAdjustmentEngine = new TierAdjustmentEngine();
    private final LayerCreditEngine layerCreditEngine = new LayerCreditEngine();
    private final TrancheHoldbackCalculator trancheHoldbackCalculator = new TrancheHoldbackCalculator();
    private final EligibilityRules eligibilityRules = new EligibilityRules();

    public AttachmentProcessor(AttachmentConfig config) {
        this.config = config;
    }

    public List<ProcessedAttachment> process(List<Attachment> attachments) {
        List<ProcessedAttachment> processed = new ArrayList<>();
        for (Attachment recovery : attachments) {
            if (!eligibilityRules.isApproved(recovery) || !eligibilityRules.hasLossAmount(recovery)) {
                continue;
            }
            if (!eligibilityRules.meetsMinimum(recovery, config)) {
                continue;
            }

            BigDecimal baseAttachment = baseAttachmentCalculator.baseAttachment(recovery, config);
            BigDecimal processingFeeAmount = processingFeeCalculator.processingFeeAmount(recovery, config);
            BigDecimal adjustmentRate = tierAdjustmentEngine.adjustmentRate(recovery, config);
            BigDecimal layerCreditAmount = layerCreditEngine.layerCreditAmount(recovery, baseAttachment, config);
            BigDecimal tierAdjustmentAmount = tierAdjustmentEngine.tierAdjustmentAmount(
                    recovery, baseAttachment, layerCreditAmount, config
            );
            BigDecimal trancheHoldbackAmount = trancheHoldbackCalculator.trancheHoldbackAmount(
                    recovery, baseAttachment, tierAdjustmentAmount, layerCreditAmount, processingFeeAmount, config
            );
            BigDecimal netAttachment = FinancePolicy.netAttachment(
                    baseAttachment, tierAdjustmentAmount, layerCreditAmount, processingFeeAmount, trancheHoldbackAmount
            );

            processed.add(new ProcessedAttachment(
                    recovery.getId(),
                    recovery.getCedent(),
                    recovery.getLossAmount(),
                    recovery.getTreatyTier(),
                    baseAttachment,
                    processingFeeAmount,
                    adjustmentRate,
                    tierAdjustmentAmount,
                    layerCreditAmount,
                    trancheHoldbackAmount,
                    netAttachment
            ));
        }

        processed.sort(Comparator.comparing(ProcessedAttachment::getId));
        return processed;
    }
}
EOF
