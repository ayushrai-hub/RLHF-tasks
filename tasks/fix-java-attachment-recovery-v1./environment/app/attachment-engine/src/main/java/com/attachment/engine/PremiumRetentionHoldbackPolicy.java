package com.attachment.engine;

import java.math.BigDecimal;

/** Production tranche holdback policy for premium loss lines. */
public class PremiumRetentionHoldbackPolicy {
    public static BigDecimal trancheHoldbackRate(
            BigDecimal exposureAmount,
            BigDecimal premiumThreshold,
            BigDecimal baseRate,
            BigDecimal premiumRate
    ) {
        if (exposureAmount.compareTo(premiumThreshold) >= 0) {
            return premiumRate;
        }
        return baseRate;
    }
}
