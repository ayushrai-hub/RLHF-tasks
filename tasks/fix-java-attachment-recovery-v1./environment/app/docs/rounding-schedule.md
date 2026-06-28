# Rounding Schedule

All money fields serialize with two decimal places (half-up unless noted).

| Component | Default | Exception |
|-----------|---------|-----------|
| baseAttachment | HALF_UP | — |
| processingFeeAmount | HALF_UP | — |
| tierAdjustmentAmount | HALF_UP | HALF_DOWN when plus tier on layer line; HALF_DOWN when premium tier on premium loss line |
| layerCreditAmount | HALF_UP | HALF_DOWN when premium treaty tier |
| trancheHoldbackAmount | HALF_UP | HALF_DOWN on layer lines |
| netAttachment | HALF_UP | — |

Premium loss line detection uses loss amount only (see config-keys.md).
