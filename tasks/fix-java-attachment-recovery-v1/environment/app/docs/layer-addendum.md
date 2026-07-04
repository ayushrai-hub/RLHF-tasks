# Layer Credit Addendum

When `exposureAmount >= attachment.threshold.layer`:

1. Compute layer credit on **baseAttachment** (not exposureAmount).
2. Use `layer.credit.rate` unless both layer line and premium loss line apply,
   then use `attachment.rate.layer.premium`.
3. Round HALF_DOWN for premium treaty tier; otherwise HALF_UP.

## Post-layer tier adjustment basis

For premium or plus treaty tiers on layer lines, tier adjustment basis is
`baseAttachment - layerCreditAmount` (not raw exposureAmount).
