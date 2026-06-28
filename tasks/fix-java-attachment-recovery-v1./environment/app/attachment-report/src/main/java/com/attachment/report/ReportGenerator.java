package com.attachment.report;

import com.google.gson.Gson;

import java.io.IOException;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class ReportGenerator {
    private static final Gson GSON = new Gson();

    public void writeReport(List<ProcessedAttachment> attachments, Path outputPath) throws IOException {
        BigDecimal totalBaseAttachment = BigDecimal.ZERO;
        BigDecimal totalTierAdjustment = BigDecimal.ZERO;
        BigDecimal totalLayerCredit = BigDecimal.ZERO;
        BigDecimal totalTrancheHoldback = BigDecimal.ZERO;

        List<Map<String, Object>> rows = attachments.stream().map(recovery -> {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("id", recovery.getId());
            row.put("obligor", recovery.getCedent());
            row.put("exposureAmount", recovery.getLossAmount());
            row.put("programTier", recovery.getTreatyTier());
            row.put("baseAttachment", recovery.getBaseAttachment());
            row.put("adjustmentRate", recovery.getAdjustmentRate());
            row.put("tierAdjustmentAmount", recovery.getTierAdjustmentAmount());
            row.put("layerCreditAmount", recovery.getCatastropheCreditAmount());
            row.put("trancheHoldbackAmount", recovery.getRetentionHoldbackAmount());
            row.put("netAttachment", recovery.getNetAttachment());
            return row;
        }).toList();

        for (ProcessedAttachment recovery : attachments) {
            totalBaseAttachment = totalBaseAttachment.add(recovery.getBaseAttachment());
            totalTierAdjustment = totalTierAdjustment.add(recovery.getTierAdjustmentAmount());
            totalLayerCredit = totalLayerCredit.add(recovery.getCatastropheCreditAmount());
            totalTrancheHoldback = totalTrancheHoldback.add(recovery.getRetentionHoldbackAmount());
        }

        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("attachmentCount", attachments.size());
        summary.put("totalBaseAttachment", totalBaseAttachment);
        summary.put("totalTierAdjustment", totalTierAdjustment);
        summary.put("totalLayerCredit", totalLayerCredit);
        summary.put("totalTrancheHoldback", totalTrancheHoldback);
        summary.put("totalAttachment", totalBaseAttachment);

        Map<String, Object> report = new LinkedHashMap<>();
        report.put("attachments", rows);
        report.put("summary", summary);

        Files.createDirectories(outputPath.getParent());
        Files.writeString(outputPath, GSON.toJson(report));
    }
}
