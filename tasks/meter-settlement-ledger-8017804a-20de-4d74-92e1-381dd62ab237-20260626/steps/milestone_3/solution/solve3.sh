#!/bin/bash
set -euo pipefail

node <<'NODE'
const fs = require("fs")
const path = require("path")
const { execFileSync } = require("child_process")

const appDir = "/app"
const catalogDb = path.join(appDir, "catalog", "meter_catalog.db")
const settlementDb = path.join(appDir, "output", "settlement.db")
const priorPath = path.join(appDir, "prior-ledger", "prior-account-months.csv")
const outputPath = path.join(appDir, "output", "reconciliation-report.json")

function queryJson(dbPath, sql) {
  const out = execFileSync("sqlite3", ["-json", dbPath, sql], { encoding: "utf8" })
  return out.trim() ? JSON.parse(out) : []
}

function splitCsv(line) {
  const cells = []
  let current = ""
  let quoted = false
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i]
    if (ch === '"') {
      if (quoted && line[i + 1] === '"') {
        current += '"'
        i += 1
      } else {
        quoted = !quoted
      }
    } else if (ch === "," && !quoted) {
      cells.push(current)
      current = ""
    } else {
      current += ch
    }
  }
  cells.push(current)
  return cells
}

function round3(value) {
  return Math.round((value + 1e-12) * 1000) / 1000
}

function keyOf(row) {
  return `${row.account_id}\u0000${row.service_month}\u0000${row.district}`
}

const settlementRows = new Map()
for (const row of queryJson(
  settlementDb,
  `SELECT account_id, service_month, district, adjusted_kwh, total_cents FROM account_months`
)) {
  settlementRows.set(keyOf(row), {
    account_id: row.account_id,
    service_month: row.service_month,
    district: row.district,
    settlement_kwh: Number(row.adjusted_kwh),
    settlement_total_cents: Number(row.total_cents)
  })
}

const priorRows = new Map()
const lines = fs.readFileSync(priorPath, "utf8").trim().split(/\r?\n/)
const header = splitCsv(lines.shift())
for (const line of lines) {
  if (!line.trim()) {
    continue
  }
  const values = splitCsv(line)
  const row = Object.fromEntries(header.map((name, index) => [name, values[index]]))
  priorRows.set(keyOf(row), {
    account_id: row.account_id,
    service_month: row.service_month,
    district: row.district,
    prior_kwh: Number(row.prior_adjusted_kwh),
    prior_total_cents: Number(row.prior_total_cents)
  })
}

const adjustments = new Map()
for (const row of queryJson(
  catalogDb,
  `SELECT account_id, service_month, district, adjustment_cents, reason FROM manual_adjustments`
)) {
  adjustments.set(keyOf(row), {
    adjustment_cents: Number(row.adjustment_cents),
    adjustment_reason: row.reason
  })
}

const rows = []
for (const key of new Set([...settlementRows.keys(), ...priorRows.keys()])) {
  const current = settlementRows.get(key)
  const prior = priorRows.get(key)
  const adjustment = adjustments.get(key) || { adjustment_cents: 0, adjustment_reason: null }
  let account_id
  let service_month
  let district
  if (current) {
    ;({ account_id, service_month, district } = current)
  } else {
    ;({ account_id, service_month, district } = prior)
  }

  const currentTotal = current ? current.settlement_total_cents : null
  const priorTotal = prior ? prior.prior_total_cents : null
  const currentKwh = current ? round3(current.settlement_kwh) : null
  const priorKwh = prior ? round3(prior.prior_kwh) : null
  let status
  if (!prior) {
    status = "new"
  } else if (!current) {
    status = "missing_from_settlement"
  } else if (currentTotal === priorTotal && currentKwh === priorKwh) {
    status = "unchanged"
  } else {
    status = "changed"
  }

  rows.push({
    account_id,
    service_month,
    district,
    status,
    settlement_total_cents: currentTotal,
    prior_total_cents: priorTotal,
    delta_cents: (currentTotal ?? 0) - (priorTotal ?? 0),
    settlement_kwh: currentKwh,
    prior_kwh: priorKwh,
    delta_kwh: round3((currentKwh ?? 0) - (priorKwh ?? 0)),
    adjustment_cents: adjustment.adjustment_cents,
    adjustment_reason: adjustment.adjustment_reason,
    final_total_cents: currentTotal === null ? null : currentTotal + adjustment.adjustment_cents
  })
}

rows.sort((a, b) => (
  a.service_month.localeCompare(b.service_month) ||
  a.account_id.localeCompare(b.account_id) ||
  a.district.localeCompare(b.district)
))

const statusCounts = { changed: 0, missing_from_settlement: 0, new: 0, unchanged: 0 }
for (const row of rows) {
  statusCounts[row.status] += 1
}

const report = {
  generated_from: ["/app/output/settlement.db", "/app/prior-ledger/prior-account-months.csv"],
  row_count: rows.length,
  status_counts: statusCounts,
  net_delta_cents: rows.reduce((sum, row) => sum + row.delta_cents, 0),
  net_adjustment_cents: rows.reduce((sum, row) => sum + row.adjustment_cents, 0),
  final_total_cents: rows.reduce((sum, row) => sum + (row.final_total_cents ?? 0), 0),
  rows
}

fs.writeFileSync(outputPath, JSON.stringify(report, null, 2) + "\n")
NODE
