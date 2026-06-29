# Production Config Key Map

Maps business parameters to keys in `/app/config/attachment-rules.properties`.
Only the production keys documented here drive nightly batch totals. Other
entries in the same file are legacy staging aliases and must be ignored.

## Terminology

| Term | Meaning | Used for |
|------|---------|----------|
| **programTier** | Label on the attachment row: `premium`, `plus`, or `basic` | `adjustment.tier.<programTier>` lookup, layer-line tier adjustment basis, some rounding modes |

Report output must echo each recovery's `programTier` string exactly as provided in
the input JSON. Config lookups normalize tier names for rate selection only.
| **premium loss line** | `exposureAmount >= attachment.threshold.exposure.premium` | Premium layer credit rate, premium holdback rate |
| **layer line** | `exposureAmount >= attachment.threshold.layer` | Layer credit eligibility, post-layer tier adjustment basis |

Premium loss-line rates depend on **loss amount only**, not on `programTier`.
A plus-tier or basic-tier recovery can still be a premium loss line when the amount
crosses the threshold.

## Core keys

| Parameter | Production property key |
|-----------|-------------------------|
| Minimum recovery amount | `minimum.attachment.amount` |
| Base attachment rate | `base.attachment.rate` |
| Processing fee rate | `processing.fee.rate` |
| Standard layer credit rate | `layer.credit.rate` |
| Base tranche holdback rate | `tranche.holdback.rate` |
| Tier adjustment rates | `adjustment.tier.<programTier>` (lowercase suffix) |
| Layer threshold | `attachment.threshold.layer` |

## Premium loss parameters

Premium exposure pricing uses the `attachment.*` keys below.

| Parameter | Production property key |
|-----------|-------------------------|
| Premium loss amount threshold | `attachment.threshold.exposure.premium` |
| Premium layer credit rate | `attachment.rate.layer.premium` |
| Premium tranche holdback rate | `attachment.rate.holdback.premium` |

Apply premium layer credit rate when **both**:

- the recovery qualifies as a layer line (`exposureAmount >= attachment.threshold.layer`), and
- `exposureAmount >= attachment.threshold.exposure.premium`

Apply premium holdback rate when `exposureAmount >= attachment.threshold.exposure.premium`
alone — on any premium loss line, regardless of `programTier`.

## Loader requirements

Production batch loaders consume `/app/config/attachment-rules.properties` directly.
Ignore `attachment-rules.override.properties` and other staging-only property aliases.

Treaty tier parameters are read from `adjustment.tier.<programTier>` entries
using the lowercase suffix shown in the config file.
