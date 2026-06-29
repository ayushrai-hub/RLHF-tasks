#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(jsonlite)
})

lake <- Sys.getenv("DATALAKE_DIR", "/app/data")
cycle_start <- "2025-03-01"
cycle_end <- "2025-03-31"
cycle_days <- 31

plan_rows <- read_csv(file.path(lake, "plans.csv"), show_col_types = FALSE)
subs <- read_csv(file.path(lake, "subscriptions.csv"), show_col_types = FALSE)
changes_raw <- read_csv(file.path(lake, "plan_changes.csv"), show_col_types = FALSE)
corrections_raw <- read_csv(
  file.path(lake, "subscription_status_corrections.csv"),
  show_col_types = FALSE
)
sessions <- read_csv(file.path(lake, "usage_data_sessions.csv"), show_col_types = FALSE)
calls <- read_tsv(file.path(lake, "usage_voice_calls.tsv"), show_col_types = FALSE)

# Rate card in force for the cycle: per plan, the latest effective_date on or
# before the cycle start. Per-plan lookup vectors for each card field.
cards <- plan_rows %>%
  filter(effective_date <= cycle_start) %>%
  group_by(plan_id) %>%
  slice_max(effective_date, n = 1, with_ties = FALSE) %>%
  ungroup()

fee_by <- setNames(cards$monthly_fee_usd, cards$plan_id)
data_allow_by <- setNames(cards$included_data_mb, cards$plan_id)
voice_allow_by <- setNames(cards$included_voice_min, cards$plan_id)
data_rate_by <- setNames(cards$overage_data_per_mb_usd, cards$plan_id)
voice_rate_by <- setNames(cards$overage_voice_per_min_usd, cards$plan_id)
tier_by <- setNames(cards$tier, cards$plan_id)

# Authoritative billed status: a correction on or before the cycle end overrides
# subscriptions.csv; later restatements are ignored.
applied <- corrections_raw %>% filter(correction_date <= cycle_end)
corrected_by <- setNames(applied$corrected_status, applied$subscription_id)

# In-cycle plan changes: keyed by subscription, the previous plan and the day the
# new plan took effect.
changes <- changes_raw %>%
  filter(substr(effective_date, 1, 7) == "2025-03") %>%
  transmute(
    subscription_id,
    prev_plan_id,
    eff_day = as.integer(substr(effective_date, 9, 10))
  )

# Valid, in-cycle, distinct usage, stamped with the day-of-month and joined to the
# subscription's change day so each row falls in the pre- or post-change period.
data_use <- sessions %>%
  filter(substr(ts, 1, 7) == "2025-03") %>%
  distinct(session_id, .keep_all = TRUE) %>%
  filter(bytes_used >= 0) %>%
  transmute(
    subscription_id,
    day = as.integer(substr(ts, 9, 10)),
    mb = bytes_used / 1e6
  ) %>%
  left_join(changes %>% select(subscription_id, eff_day), by = "subscription_id") %>%
  group_by(subscription_id) %>%
  summarise(
    total_mb = sum(mb),
    before_mb = sum(if_else(!is.na(eff_day) & day < eff_day, mb, 0)),
    after_mb = sum(if_else(!is.na(eff_day) & day >= eff_day, mb, 0)),
    .groups = "drop"
  )

voice_use <- calls %>%
  filter(substr(ts, 1, 7) == "2025-03") %>%
  distinct(call_id, .keep_all = TRUE) %>%
  transmute(
    subscription_id,
    day = as.integer(substr(ts, 9, 10)),
    minutes = duration_sec / 60
  ) %>%
  left_join(changes %>% select(subscription_id, eff_day), by = "subscription_id") %>%
  group_by(subscription_id) %>%
  summarise(
    total_min = sum(minutes),
    before_min = sum(if_else(!is.na(eff_day) & day < eff_day, minutes, 0)),
    after_min = sum(if_else(!is.na(eff_day) & day >= eff_day, minutes, 0)),
    .groups = "drop"
  )

active <- subs %>%
  mutate(eff_status = coalesce(corrected_by[subscription_id], status)) %>%
  filter(eff_status == "ACTIVE") %>%
  left_join(changes, by = "subscription_id") %>%
  left_join(data_use, by = "subscription_id") %>%
  left_join(voice_use, by = "subscription_id") %>%
  mutate(
    total_mb = coalesce(total_mb, 0),
    before_mb = coalesce(before_mb, 0),
    after_mb = coalesce(after_mb, 0),
    total_min = coalesce(total_min, 0),
    before_min = coalesce(before_min, 0),
    after_min = coalesce(after_min, 0),
    changed = !is.na(eff_day),
    tier = tier_by[plan_id],
    new_fee = fee_by[plan_id],
    new_data_allow = data_allow_by[plan_id],
    new_voice_allow = voice_allow_by[plan_id],
    new_dr = data_rate_by[plan_id],
    new_vr = voice_rate_by[plan_id],
    prev_fee = fee_by[prev_plan_id],
    prev_data_allow = data_allow_by[prev_plan_id],
    prev_voice_allow = voice_allow_by[prev_plan_id],
    prev_dr = data_rate_by[prev_plan_id],
    prev_vr = voice_rate_by[prev_plan_id],
    w_prev = (eff_day - 1) / cycle_days,
    w_new = (cycle_days - (eff_day - 1)) / cycle_days,
    recurring = if_else(changed, prev_fee * w_prev + new_fee * w_new, new_fee),
    data_overage = if_else(
      changed,
      pmax(0, before_mb - prev_data_allow * w_prev) * prev_dr +
        pmax(0, after_mb - new_data_allow * w_new) * new_dr,
      pmax(0, total_mb - new_data_allow) * new_dr
    ),
    voice_overage = if_else(
      changed,
      pmax(0, before_min - prev_voice_allow * w_prev) * prev_vr +
        pmax(0, after_min - new_voice_allow * w_new) * new_vr,
      pmax(0, total_min - new_voice_allow) * new_vr
    ),
    revenue = recurring + data_overage + voice_overage
  )

by_tier <- active %>%
  group_by(tier) %>%
  summarise(rev = sum(revenue), .groups = "drop")

by_tier_list <- as.list(setNames(by_tier$rev, by_tier$tier))

result <- list(
  answer = sum(active$revenue),
  by_tier = by_tier_list,
  recurring_total_usd = sum(active$recurring),
  data_overage_total_usd = sum(active$data_overage),
  n_active_subscriptions = nrow(active)
)

write_json(result, "/app/answer.json", auto_unbox = TRUE, digits = 10)
