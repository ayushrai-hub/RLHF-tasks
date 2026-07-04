package com.attachment.core;

import java.io.IOException;
import java.io.InputStream;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import java.util.Properties;

public class AttachmentConfigLoader {
    public static AttachmentConfig load(Path configPath) throws IOException {
        Path overridePath = configPath.getParent().resolve("attachment-rules.override.properties");
        Path selectedPath = Files.exists(overridePath) ? overridePath : configPath;

        Properties properties = new Properties();
        try (InputStream input = Files.newInputStream(selectedPath)) {
            properties.load(input);
        }

        BigDecimal minimumAttachmentAmount = new BigDecimal(properties.getProperty("minimum.recovery.total", "0.00"));
        BigDecimal baseAttachmentRate = new BigDecimal(properties.getProperty("base.attachment.rate", "0.00"));
        BigDecimal processingFeeRate = new BigDecimal(properties.getProperty("processing.fee.rate", "0.00"));
        BigDecimal layerCreditRate = new BigDecimal(properties.getProperty("layer.credit.rate", "0.00"));
        BigDecimal trancheHoldbackRate = new BigDecimal(properties.getProperty("tranche.holdback.rate", "0.00"));
        BigDecimal premiumCatRate = new BigDecimal(
                properties.getProperty("layer.credit.rate.high", layerCreditRate.toPlainString())
        );

        Map<String, BigDecimal> adjustmentRates = new HashMap<>();
        for (String key : properties.stringPropertyNames()) {
            if (key.startsWith("adjustment.tier.")) {
                String tier = key.substring("adjustment.tier.".length());
                adjustmentRates.put(tier.toUpperCase(), new BigDecimal(properties.getProperty(key)));
            }
        }

        return new AttachmentConfig(
                minimumAttachmentAmount,
                baseAttachmentRate,
                processingFeeRate,
                layerCreditRate,
                trancheHoldbackRate,
                premiumCatRate,
                trancheHoldbackRate,
                new BigDecimal("999999.99"),
                new BigDecimal("10000.00"),
                adjustmentRates
        );
    }
}
