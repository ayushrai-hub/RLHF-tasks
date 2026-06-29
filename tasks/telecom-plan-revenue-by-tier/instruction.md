You are handed the operational data lake of a mobile carrier and asked to close the
books for one billing cycle. The lake lives at /app/data and holds many exports of
customers, subscriptions, plans, usage, and assorted billing and network records.
Several of these exports describe the same things in different ways, some are kept
only for audit or marketing, and the files you need are mixed in among ones you do
not. Part of the job is deciding which exports are authoritative.

Before you write any code, list the contents of /app/data and read the data
dictionary in full. The exact file names, the column names, and the units are the
ones documented there, not the ones you might assume from experience: the rate
card is stamped with a single effective_date column rather than an effective
from/to pair, data allowances and usage are in megabytes and bytes rather than
gigabytes, and several files are decoys kept only for audit or marketing. Coding
against assumed schema conventions before you have read the codebook and seen the
actual files is the most common way this task is failed.

Your task is to compute the total billed plan revenue for the March 2025 billing
cycle and break it down by plan tier. Billed plan revenue means the monthly
recurring plan fees plus metered data and voice overage, summed across the
subscriptions that are actually billed for the cycle. The data dictionary at
/app/docs/codebook.md defines the billing cycle, the subscription statuses that are
billed, the plan catalog fields, the units that usage is recorded in, the sentinel
that marks voided usage, the exact billing formula, and what is out of scope. It also
covers several billing wrinkles that materially change the result and are easy to
miss: the plan catalog is effective-dated and carries more than one rate card per
plan, an authoritative restatement revises the billed status of some subscriptions,
and some subscriptions change plan partway through the cycle. The codebook is precise
about how each of these is handled for the cycle; work the consequences out from it
rather than from the obvious reading of the files. Read it before you start, and
follow its conventions precisely. The
precise question and the required output fields are restated at /app/docs/question.md.

Write your analysis as an R script at /app/analysis.R. It must read the lake from
the directory named by the DATALAKE_DIR environment variable, falling back to
/app/data when that variable is not set, so the same script can be pointed at a
different copy of the lake without edits. Provided input helpers are available at
/app/R/io_helpers.R if you want them, but you are free to read the files however
you like.

Running your script must write the result to /app/answer.json as a JSON object with
these fields: answer, the total billed plan revenue in US dollars as a number;
by_tier, an object mapping each plan tier name to its billed plan revenue in US
dollars, with the tier values summing to answer; recurring_total_usd, the total
recurring fees billed, as a number; data_overage_total_usd, the total data overage
billed, as a number; and n_active_subscriptions, the count of billed subscriptions
as an integer. The example in /app/docs/question.md shows the exact shape.

A correct result reflects the billing conventions in the codebook applied to the
authoritative exports in the lake. The by_tier values, the recurring total, the
data overage total, and the active subscription count must all be consistent with
the same single pipeline that produces answer. Use absolute paths throughout.
