# Billing data dictionary

This lake holds operational and billing exports for a mobile carrier. Many of the
exports are retained for audit, reporting convenience, or marketing, and several
describe the same entities in different ways. The notes below define the entities,
the billing conventions, and the scope of the billing question. They do not tell
you which exports to use; identifying the authoritative source for each entity is
part of the work.

## Billing cycle

The cycle of interest is March 2025, covering 2025-03-01 through 2025-03-31
inclusive. Each usage row carries a timestamp in its ts field, and a usage row
belongs to the cycle only when that timestamp falls inside the window. Separate
prior-cycle exports are retained for audit, and some of the usage exports also
carry a minority of rows whose timestamps fall just outside the window, in late
February or early April; those rows belong to an adjacent cycle and are not counted
here. Decide whether a usage row counts from its timestamp, not from the file it
sits in.

## Repeated rows

Parts of the lake were written by a loader that retried after transient failures,
so a usage export can contain the same row more than once. A data session is
identified uniquely by its session_id and a voice call by its call_id. Count each
distinct session and each distinct call once; a repeated row whose id has already
been seen adds no further usage. Whether a row counts is decided first, from its own
timestamp as described under Billing cycle; deduplicate by id among the rows that
count for the cycle, so that a retried copy of an in-cycle row collapses to one.

## Subscriptions

A subscription is one customer line on one plan for a billing cycle. Each
subscription has a status: ACTIVE, SUSPENDED, or CANCELLED. Only ACTIVE
subscriptions are billed for the cycle. Suspended and cancelled subscriptions are
not billed even if usage rows exist for them.

The status recorded in the subscription export is not the last word. The carrier
issues an authoritative status restatement, stamped with the date on which the
correction was made, that supersedes the recorded status for billing. A correction
applies to this cycle when its correction date is on or before the last day of the
cycle: a line restated to CANCELLED on or before that date is not billed even if its
recorded status is ACTIVE, and a line restated to ACTIVE on or before that date is
billed even if its recorded status is SUSPENDED or CANCELLED. Corrections dated after
the cycle has closed are restatements of a later cycle and do not apply here. A
subscription with no correction keeps its recorded status. The billed set for the
cycle is the set of subscriptions whose status, after corrections are applied, is
ACTIVE; everywhere below, "ACTIVE" and "billed" mean this corrected status.

## Plan catalog

The contracted plan catalog gives, per plan, the tier (BRONZE, SILVER, GOLD, or
UNLIMITED), the monthly recurring fee in US dollars, the included data allowance in
megabytes, the included voice allowance in minutes, the per megabyte data overage
rate, and the per minute voice overage rate. Promotional sheets and list-price
material describe prices that are not the contracted price and are not used for
billing. The UNLIMITED tier includes unlimited voice, so it never incurs voice
overage.

The catalog is an effective-dated rate card: it carries more than one row per plan,
each stamped with the effective_date on which that card took effect. A plan's older
cards are kept for audit and a newly published card may already be present even
though it does not take effect until a later cycle. The card that governs billing
for a cycle is the one whose effective_date is the latest that is on or before the
first day of the cycle; cards whose effective_date is after the cycle has begun have
not taken effect and are not used. A plan's tier is stable across its cards. All fee,
allowance, and overage figures used below come from the cycle-effective card.

## Mid-cycle plan changes

A subscription can move from one plan to another partway through the cycle. Each such
move is recorded as a change row carrying the subscription, the previous plan, the
new plan, and the effective_date on which the new plan took effect. The plan named
for the subscription in the subscription records is the plan in force at the end of
the cycle, that is, the new plan of any in-cycle change.

A change row affects this cycle's billing only when its effective_date falls inside
the cycle window and the subscription is one that is billed for the cycle; change
rows dated outside the window, or belonging to subscriptions that are not billed, are
history that does not apply here. An affected subscription has exactly one such
in-cycle change.

For a subscription with an in-cycle change, the change effective day splits the cycle
into two periods. If the new plan takes effect on the Nth day of the cycle, the
previous plan holds for the first N minus one days (the previous-plan period) and the
new plan holds from the Nth day through the last day, the Nth day counting as a
new-plan day (the new-plan period). The two periods cover all 31 days; when N is the
first day the previous-plan period is empty, and the whole cycle is the new plan.

Both the recurring fee and the included allowances are prorated across these two
periods, each side priced from its own plan's cycle-effective card:

  - Recurring fee. The previous plan is charged for its share of the 31 days and the
    new plan for its share, so the fee is previous_fee times (N minus 1) over 31 plus
    new_fee times (31 minus (N minus 1)) over 31. A subscription with no in-cycle
    change is charged the full recurring fee of its plan.

  - Included allowances. Each period gets only its day-weighted share of its own
    plan's monthly allowance: the previous-plan period's data allowance is the
    previous plan's included data times (N minus 1) over 31, and the new-plan period's
    data allowance is the new plan's included data times (31 minus (N minus 1)) over
    31; voice allowances are split the same way. Usage is attributed to a period by
    the day in its timestamp: a usage row dated before the Nth day belongs to the
    previous-plan period, and a row dated on or after the Nth day belongs to the
    new-plan period. Overage is then computed within each period, against that
    period's prorated allowance and at that period's own overage rate, and the two
    periods' overages are summed.

A subscription with no in-cycle change uses its plan's full monthly allowances and
overage rates against its whole-cycle usage, as elsewhere. A subscription's tier is
always that of its end-of-cycle plan, and each billed subscription's revenue,
including the prorated recurring portion and the per-period overage, is attributed in
full to its end-of-cycle tier.

## Data usage

Data usage is recorded one row per session. The data volume of a session is given
in bytes. Convert bytes to megabytes by dividing by 1,000,000. A volume value of
-1 is a sentinel marking a dropped or voided session that carried no billable
traffic; such rows are excluded from the data total. A subscription's billable data
for the cycle is the sum, in megabytes, of its valid, in-cycle, distinct sessions.

## Voice usage

Voice usage is recorded one row per call. The duration of a call is given in
seconds. Convert seconds to minutes by dividing by 60. A subscription's billable
voice for the cycle is the sum, in minutes, of its in-cycle, distinct calls.

## How a subscription is billed

For each billed (corrected-ACTIVE) subscription in the cycle, the billed amount is the
recurring fee, plus data overage, plus voice overage. The recurring fee is the plan's
monthly fee for a subscription with no in-cycle plan change, or the day-prorated fee
described under Mid-cycle plan changes for a subscription that changed plan during the
cycle, charged once per subscription for the cycle.

For a subscription with no in-cycle plan change, overage uses the end-of-cycle plan's
cycle-effective card and the subscription's whole-cycle billable usage:

  data overage  = max(0, used_mb - included_data_mb) * data overage rate
  voice overage = max(0, used_min - included_voice_min) * voice overage rate

For a subscription with an in-cycle plan change, overage is computed per period as
described under Mid-cycle plan changes: each period's billable usage is charged
against that period's prorated allowance at that period's own overage rate, and the
two periods' overages are summed. The UNLIMITED tier includes unlimited voice in
every period, so it never incurs voice overage.

## Out of scope

Taxes, promotions and discounts, device installment plans, roaming charges,
billing adjustments, and credit notes are out of scope for this question. They are
present in the lake but do not enter the billed plan revenue you are asked to
compute.
