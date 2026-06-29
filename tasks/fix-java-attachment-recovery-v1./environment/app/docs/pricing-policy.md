# Reinsurance Attachment Pricing Policy

Numeric parameters live in `/app/config/attachment-rules.properties`. Production
batch jobs must ignore `attachment-rules.override.properties` and other staging
aliases.

## Report structure

Write `/app/output/attachment-report.json` with exactly three top-level keys:
`generatedAt`, `attachments`, and `summary`. Do not rename these keys.

The `attachments` array holds one object per included row. The `summary` object
holds rollups listed in the Summary block below.

## Eligibility

A recovery is included when **all** of the following hold:

- `status` matches approved **case-insensitively**. Values such as `"approved"`,
  `"Approved"`, and `"APPROVED"` all qualify; `"pending"` does not.
- `exposureAmount` is greater than zero
- loss amount is greater than or equal to `minimum.attachment.amount`

## Base attachment

`baseAttachment = exposureAmount × base.attachment.rate`, rounded half-up to two decimals.

## Processing fee

`processingFeeAmount = exposureAmount × processing.fee.rate`, rounded half-up to two
decimals. The fee increases the tranche holdback base.

## Tier adjustment

Read `adjustment.tier.<programTier>`. Default:
`tierAdjustmentAmount = baseAttachment × tierRate`, rounded half-up.

Layer-line tier adjustment basis and rounding exceptions are in
`/app/docs/layer-addendum.md`, `/app/docs/config-keys.md`, and
`/app/docs/rounding-schedule.md`.

## Layer credit adjustment

When `exposureAmount >= attachment.threshold.layer`, apply a layer credit using
config rates. Default layer credit rounding is half-up.

The credit amount is computed on **base attachment**, not raw loss amount:

`layerCreditAmount = baseAttachment × rate`

Premium layer rates and tier-specific rounding are defined in the addenda above.

## Tranche holdback

See `/app/docs/tranche-holdback-addendum.md` and `/app/docs/config-keys.md`.

## Net recovery

`netAttachment = baseAttachment - tierAdjustmentAmount - layerCreditAmount + processingFeeAmount - trancheHoldbackAmount`

## Sorting

Sort included attachments by `netAttachment` descending. Break ties using `id` ascending.

## Summary block

- `attachmentCount`, `totalBaseAttachment`, `totalProcessingFee`, `totalTierAdjustment`,
  `totalLayerCredit`, `totalTrancheHoldback`, `totalAttachment`

## Report metadata

Include `generatedAt` as UTC ISO-8601 ending with `Z`.

Each attachment row: `id`, `obligor`, `exposureAmount`, `programTier`, `baseAttachment`,
`processingFeeAmount`, `adjustmentRate`, `tierAdjustmentAmount`, `layerCreditAmount`,
`trancheHoldbackAmount`, `netAttachment`.

## Pass-through row fields

Copy `id`, `obligor`, `exposureAmount`, and `programTier` from the input recovery
unchanged. Preserve the original string casing of `programTier` exactly as it
appears in `/app/data/attachments.json` (for example `PREMIUM` must stay `PREMIUM`).

Rate lookups use case-insensitive tier matching against config keys; that
normalization applies to calculations only, not to the serialized report row.

## JSON money serialization

Money fields must be **JSON number literals** with exactly two decimal places in
the serialized text — not JSON strings. For example `"exposureAmount": 1500.00` is
correct; `"exposureAmount": "1500.00"` is not.

Report `adjustmentRate` the same way (for example `0.00` for basic tier, not `0`).

Use Gson pretty-printing with a space after each colon (for example
`"exposureAmount": 1500.00`, not `"exposureAmount":1500.00`).
