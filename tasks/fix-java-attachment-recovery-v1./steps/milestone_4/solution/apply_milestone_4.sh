#!/bin/bash
set -eo pipefail

cd /app

cat > attachment-report/src/main/java/com/attachment/report/FinancePolicy.java << 'EOF'
package com.attachment.report;

import java.math.BigDecimal;
import java.math.RoundingMode;

public class FinancePolicy {
    public static BigDecimal netAttachment(
            BigDecimal baseAttachment,
            BigDecimal tierAdjustmentAmount,
            BigDecimal layerCreditAmount,
            BigDecimal processingFeeAmount,
            BigDecimal trancheHoldbackAmount
    ) {
        return baseAttachment
                .subtract(tierAdjustmentAmount)
                .subtract(layerCreditAmount)
                .add(processingFeeAmount)
                .subtract(trancheHoldbackAmount)
                .setScale(2, RoundingMode.HALF_UP);
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

        processed.sort(
                Comparator.comparing(ProcessedAttachment::getNetAttachment)
                        .reversed()
                        .thenComparing(ProcessedAttachment::getId)
        );
        return processed;
    }
}
EOF

cat > attachment-report/src/main/java/com/attachment/report/ReportGenerator.java << 'EOF'
package com.attachment.report;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

import java.io.IOException;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class ReportGenerator {
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();

    public void writeReport(List<ProcessedAttachment> attachments, Path outputPath) throws IOException {
        BigDecimal totalBaseAttachment = BigDecimal.ZERO;
        BigDecimal totalProcessingFee = BigDecimal.ZERO;
        BigDecimal totalTierAdjustment = BigDecimal.ZERO;
        BigDecimal totalLayerCredit = BigDecimal.ZERO;
        BigDecimal totalTrancheHoldback = BigDecimal.ZERO;
        BigDecimal totalAttachment = BigDecimal.ZERO;

        List<Map<String, Object>> rows = attachments.stream().map(recovery -> {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("id", recovery.getId());
            row.put("obligor", recovery.getCedent());
            row.put("exposureAmount", scaleMoney(recovery.getLossAmount()));
            row.put("programTier", recovery.getTreatyTier());
            row.put("baseAttachment", scaleMoney(recovery.getBaseAttachment()));
            row.put("processingFeeAmount", scaleMoney(recovery.getProcessingFeeAmount()));
            row.put("adjustmentRate", scaleRate(recovery.getAdjustmentRate()));
            row.put("tierAdjustmentAmount", scaleMoney(recovery.getTierAdjustmentAmount()));
            row.put("layerCreditAmount", scaleMoney(recovery.getCatastropheCreditAmount()));
            row.put("trancheHoldbackAmount", scaleMoney(recovery.getRetentionHoldbackAmount()));
            row.put("netAttachment", scaleMoney(recovery.getNetAttachment()));
            return row;
        }).toList();

        for (ProcessedAttachment recovery : attachments) {
            totalBaseAttachment = totalBaseAttachment.add(recovery.getBaseAttachment());
            totalProcessingFee = totalProcessingFee.add(recovery.getProcessingFeeAmount());
            totalTierAdjustment = totalTierAdjustment.add(recovery.getTierAdjustmentAmount());
            totalLayerCredit = totalLayerCredit.add(recovery.getCatastropheCreditAmount());
            totalTrancheHoldback = totalTrancheHoldback.add(recovery.getRetentionHoldbackAmount());
            totalAttachment = totalAttachment.add(recovery.getNetAttachment());
        }

        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("attachmentCount", attachments.size());
        summary.put("totalBaseAttachment", scaleMoney(totalBaseAttachment));
        summary.put("totalProcessingFee", scaleMoney(totalProcessingFee));
        summary.put("totalTierAdjustment", scaleMoney(totalTierAdjustment));
        summary.put("totalLayerCredit", scaleMoney(totalLayerCredit));
        summary.put("totalTrancheHoldback", scaleMoney(totalTrancheHoldback));
        summary.put("totalAttachment", scaleMoney(totalAttachment));

        Map<String, Object> report = new LinkedHashMap<>();
        report.put("generatedAt", Instant.now().toString());
        report.put("attachments", rows);
        report.put("summary", summary);

        Files.createDirectories(outputPath.getParent());
        Files.writeString(outputPath, GSON.toJson(report));
    }

    private BigDecimal scaleMoney(BigDecimal value) {
        return value.setScale(2, RoundingMode.HALF_UP);
    }

    private BigDecimal scaleRate(BigDecimal value) {
        return value.setScale(2, RoundingMode.HALF_UP);
    }
}
EOF
