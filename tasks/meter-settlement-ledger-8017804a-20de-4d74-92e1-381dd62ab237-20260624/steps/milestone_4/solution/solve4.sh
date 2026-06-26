#!/bin/bash
set -euo pipefail

node <<'NODE'
const fs = require("fs")
const path = require("path")

const appDir = "/app"
const reportPath = path.join(appDir, "output", "reconciliation-report.json")
const summaryPath = path.join(appDir, "output", "settlement-summary.json")
const outputPath = path.join(appDir, "output", "district-review.json")

const report = JSON.parse(fs.readFileSync(reportPath, "utf8"))
const summary = JSON.parse(fs.readFileSync(summaryPath, "utf8"))

const statusKeys = ["changed", "missing_from_settlement", "new", "unchanged"]
const bucketKeys = ["adjusted_variance", "missing_current", "new_current", "routine", "usage_swing"]
const priorityScores = {
  missing_current: 100,
  new_current: 80,
  adjusted_variance: 60,
  usage_swing: 40,
  routine: 0
}

function emptyCounts(keys) {
  return Object.fromEntries(keys.map(key => [key, 0]))
}

function reviewBucket(row) {
  if (row.status === "missing_from_settlement" && (row.prior_total_cents ?? 0) > 0) {
    return "missing_current"
  }
  if (row.status === "new") {
    return "new_current"
  }
  if (row.adjustment_cents !== 0 && Math.abs(row.delta_cents) >= 5) {
    return "adjusted_variance"
  }
  if (
    row.settlement_kwh !== null &&
    row.prior_kwh !== null &&
    Math.abs(row.delta_kwh) >= 0.5
  ) {
    return "usage_swing"
  }
  return "routine"
}

const summaryDistricts = new Map()
for (const district of summary.districts || []) {
  summaryDistricts.set(district.district, district)
}

const rowsWithBuckets = report.rows.map(row => ({
  ...row,
  review_bucket: reviewBucket(row)
}))

const reviewMonths = [...new Set(rowsWithBuckets.map(row => row.service_month))].sort()
const districts = []

for (const districtName of [...new Set(rowsWithBuckets.map(row => row.district))].sort()) {
  const districtRows = rowsWithBuckets.filter(row => row.district === districtName)
  const statusCounts = emptyCounts(statusKeys)
  const bucketCounts = emptyCounts(bucketKeys)
  for (const row of districtRows) {
    statusCounts[row.status] += 1
    bucketCounts[row.review_bucket] += 1
  }

  const largest = [...districtRows].sort((a, b) => (
    Math.abs(b.delta_cents) - Math.abs(a.delta_cents) ||
    a.service_month.localeCompare(b.service_month) ||
    a.account_id.localeCompare(b.account_id) ||
    a.district.localeCompare(b.district)
  ))[0]

  districts.push({
    district: districtName,
    settlement_account_month_count: summaryDistricts.get(districtName)?.account_month_count ?? 0,
    reconciliation_row_count: districtRows.length,
    status_counts: statusCounts,
    review_bucket_counts: bucketCounts,
    settlement_total_cents: districtRows.reduce((sum, row) => sum + (row.settlement_total_cents ?? 0), 0),
    prior_total_cents: districtRows.reduce((sum, row) => sum + (row.prior_total_cents ?? 0), 0),
    delta_cents: districtRows.reduce((sum, row) => sum + row.delta_cents, 0),
    adjustment_cents: districtRows.reduce((sum, row) => sum + row.adjustment_cents, 0),
    final_total_cents: districtRows.reduce((sum, row) => sum + (row.final_total_cents ?? 0), 0),
    largest_abs_delta: {
      account_id: largest.account_id,
      service_month: largest.service_month,
      district: largest.district,
      delta_cents: largest.delta_cents,
      delta_kwh: largest.delta_kwh
    }
  })
}

const exceptions = rowsWithBuckets
  .filter(row => row.review_bucket !== "routine")
  .map(row => ({
    account_id: row.account_id,
    service_month: row.service_month,
    district: row.district,
    review_bucket: row.review_bucket,
    priority_score: priorityScores[row.review_bucket],
    status: row.status,
    delta_cents: row.delta_cents,
    delta_kwh: row.delta_kwh,
    adjustment_cents: row.adjustment_cents,
    final_total_cents: row.final_total_cents
  }))
  .sort((a, b) => (
    b.priority_score - a.priority_score ||
    a.service_month.localeCompare(b.service_month) ||
    a.account_id.localeCompare(b.account_id) ||
    a.district.localeCompare(b.district)
  ))

const review = {
  generated_from: ["/app/output/reconciliation-report.json", "/app/output/settlement-summary.json"],
  review_months: reviewMonths,
  overall: {
    district_count: districts.length,
    account_month_count: summary.account_month_count,
    exception_count: exceptions.length,
    net_delta_cents: report.net_delta_cents,
    net_adjustment_cents: report.net_adjustment_cents,
    final_total_cents: report.final_total_cents
  },
  districts,
  exceptions
}

fs.writeFileSync(outputPath, JSON.stringify(review, null, 2) + "\n")
NODE
