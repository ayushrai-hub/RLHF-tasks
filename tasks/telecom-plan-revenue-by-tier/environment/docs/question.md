# Question and output schema

Compute the total billed plan revenue for the March 2025 billing cycle, broken
down by plan tier, following the billing conventions in codebook.md.

Write the result as JSON to /app/answer.json with exactly these fields:

  answer
    Number. Total billed plan revenue in US dollars across all billed
    (corrected-ACTIVE) subscriptions in the cycle (recurring fees plus data and
    voice overage).

  by_tier
    Object mapping each plan tier name (BRONZE, SILVER, GOLD, UNLIMITED) to the
    total billed plan revenue in US dollars for that tier. The four tier values
    sum to answer.

  recurring_total_usd
    Number. Total recurring fees billed across all billed subscriptions in the cycle,
    excluding any overage. This is the sum of each subscription's recurring charge
    after any mid-cycle proration, not a count of full monthly fees.

  data_overage_total_usd
    Number. Total data overage charges billed across all billed subscriptions in
    the cycle, summing the per-period overage for any subscription that changed plan
    mid-cycle.

  n_active_subscriptions
    Integer. The number of billed (corrected-ACTIVE) subscriptions for the cycle.

The monetary fields are graded to within a small tolerance, so reporting full
precision or rounding each amount to the nearest cent are both accepted;
n_active_subscriptions must be exact.

Example shape (values are illustrative, not the answer):

{
  "answer": 12345.67,
  "by_tier": {"BRONZE": 1000.0, "SILVER": 2000.0, "GOLD": 3000.0, "UNLIMITED": 6345.67},
  "recurring_total_usd": 11000.0,
  "data_overage_total_usd": 200.0,
  "n_active_subscriptions": 250
}
