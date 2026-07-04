# Tranche Holdback Addendum

Taxable base for tranche holdback:

`baseAttachment - tierAdjustmentAmount - layerCreditAmount + processingFeeAmount`

Premium holdback rate applies when `exposureAmount >= attachment.threshold.exposure.premium`
(amount-based, not tier-gated).

Basic tier attachments exactly at `minimum.attachment.amount` receive zero tranche holdback.

Round HALF_DOWN on layer lines; HALF_UP otherwise.
