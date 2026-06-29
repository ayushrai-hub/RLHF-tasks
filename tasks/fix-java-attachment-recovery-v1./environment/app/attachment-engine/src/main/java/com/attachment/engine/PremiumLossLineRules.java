package com.attachment.engine;

import java.math.BigDecimal;

public class PremiumLossLineRules {
    public static boolean isPremiumLossLine(BigDecimal exposureAmount, BigDecimal threshold) {
        return exposureAmount.compareTo(threshold) > 0;
    }
}
