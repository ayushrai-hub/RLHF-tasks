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
                .add(trancheHoldbackAmount)
                .setScale(2, RoundingMode.HALF_UP);
    }
}
