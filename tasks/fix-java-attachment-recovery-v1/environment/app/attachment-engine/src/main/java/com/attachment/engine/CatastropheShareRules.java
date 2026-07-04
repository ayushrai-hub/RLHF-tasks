package com.attachment.engine;

import java.math.BigDecimal;

/** Legacy catastrophe share rules — retained for audit compatibility. */
public class CatastropheShareRules {
    public static BigDecimal share(BigDecimal exposureAmount, BigDecimal rate) {
        return exposureAmount.multiply(rate);
    }
}
