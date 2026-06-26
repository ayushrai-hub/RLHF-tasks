#!/bin/bash
set -euo pipefail

node <<'NODE'
const fs = require("fs")
const path = require("path")

const appDir = "/app"
const reviewPath = path.join(appDir, "output", "district-review.json")
const reportPath = path.join(appDir, "output", "reconciliation-report.json")
const outputPath = path.join(appDir, "output", "posting-actions.json")

const review = JSON.parse(fs.readFileSync(reviewPath, "utf8"))
const report = JSON.parse(fs.readFileSync(reportPath, "utf8"))

const actionByBucket = {
  missing_current: "hold-prior-ledger",
  new_current: "review-new-account",
  unadjusted_large_delta: "investigate-unadjusted-delta",
  adjusted_variance: "review-adjustment",
  usage_swing: "review-usage-swing"
}
const actionKeys = [
  "hold-prior-ledger",
  "review-new-account",
  "investigate-unadjusted-delta",
  "review-adjustment",
  "review-usage-swing"
]
const directionKeys = [
  "add-current",
  "increase-current",
  "decrease-current",
  "reverse-prior",
  "review-no-change"
]

function emptyActionCounts() {
  return Object.fromEntries(actionKeys.map(key => [key, 0]))
}

function emptyDirectionCounts() {
  return Object.fromEntries(directionKeys.map(key => [key, 0]))
}

function reportKey(row) {
  return `${row.service_month}\u0000${row.district}\u0000${row.account_id}`
}

function postingDirection(action, postingDeltaCents) {
  if (action === "hold-prior-ledger") {
    return "reverse-prior"
  }
  if (action === "review-new-account") {
    return "add-current"
  }
  if (postingDeltaCents > 0) {
    return "increase-current"
  }
  if (postingDeltaCents < 0) {
    return "decrease-current"
  }
  return "review-no-change"
}

function sortedActions(rows) {
  return [...rows].sort((a, b) => (
    b.priority_score - a.priority_score ||
    a.service_month.localeCompare(b.service_month) ||
    a.district.localeCompare(b.district) ||
    a.account_id.localeCompare(b.account_id) ||
    a.action.localeCompare(b.action)
  ))
}

const reportRows = new Map(report.rows.map(row => [reportKey(row), row]))

const actions = sortedActions(review.exceptions.map(row => {
  const action = actionByBucket[row.review_bucket]
  const reportRow = reportRows.get(reportKey(row))
  if (!reportRow) {
    throw new Error(`missing reconciliation row for ${row.service_month} ${row.district} ${row.account_id}`)
  }
  const postingDeltaCents = (row.final_total_cents ?? 0) - (reportRow.prior_total_cents ?? 0)
  return {
    action_id: `${row.service_month}:${row.district}:${row.account_id}:${action}`,
    service_month: row.service_month,
    district: row.district,
    account_id: row.account_id,
    action,
    review_bucket: row.review_bucket,
    priority_score: row.priority_score,
    status: row.status,
    delta_cents: row.delta_cents,
    adjustment_cents: row.adjustment_cents,
    final_total_cents: row.final_total_cents,
    settlement_total_cents: reportRow.settlement_total_cents,
    prior_total_cents: reportRow.prior_total_cents,
    posting_delta_cents: postingDeltaCents,
    posting_direction: postingDirection(action, postingDeltaCents)
  }
}))

const actionCounts = emptyActionCounts()
const postingDirectionCounts = emptyDirectionCounts()
for (const row of actions) {
  actionCounts[row.action] += 1
  postingDirectionCounts[row.posting_direction] += 1
}

const districtActions = []
for (const district of [...new Set(actions.map(row => row.district))].sort()) {
  const rows = actions.filter(row => row.district === district)
  const counts = emptyActionCounts()
  const directions = emptyDirectionCounts()
  for (const row of rows) {
    counts[row.action] += 1
    directions[row.posting_direction] += 1
  }
  districtActions.push({
    district,
    exception_count: rows.length,
    highest_priority_score: Math.max(...rows.map(row => row.priority_score)),
    action_counts: counts,
    posting_direction_counts: directions,
    posting_delta_cents: rows.reduce((sum, row) => sum + row.posting_delta_cents, 0),
    final_total_cents: rows.reduce((sum, row) => sum + (row.final_total_cents ?? 0), 0)
  })
}

const monthActions = []
for (const serviceMonth of [...new Set(actions.map(row => row.service_month))].sort()) {
  const rows = actions.filter(row => row.service_month === serviceMonth)
  const counts = emptyActionCounts()
  const directions = emptyDirectionCounts()
  for (const row of rows) {
    counts[row.action] += 1
    directions[row.posting_direction] += 1
  }
  monthActions.push({
    service_month: serviceMonth,
    exception_count: rows.length,
    highest_priority_score: Math.max(...rows.map(row => row.priority_score)),
    action_counts: counts,
    posting_direction_counts: directions,
    delta_cents: rows.reduce((sum, row) => sum + row.delta_cents, 0),
    posting_delta_cents: rows.reduce((sum, row) => sum + row.posting_delta_cents, 0),
    final_total_cents: rows.reduce((sum, row) => sum + (row.final_total_cents ?? 0), 0)
  })
}

const postingActions = {
  generated_from: [reviewPath, reportPath],
  action_counts: actionCounts,
  posting_direction_counts: postingDirectionCounts,
  district_actions: districtActions,
  month_actions: monthActions,
  actions
}

fs.writeFileSync(outputPath, JSON.stringify(postingActions, null, 2) + "\n")
NODE
