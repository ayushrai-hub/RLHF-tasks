#!/bin/bash
set -euo pipefail

node <<'NODE'
const fs = require("fs")
const path = require("path")
const { execFileSync, spawnSync } = require("child_process")

const appDir = "/app"
const dbPath = path.join(appDir, "catalog", "meter_catalog.db")
const outputDir = path.join(appDir, "output")
const normalizedPath = path.join(outputDir, "normalized-events.jsonl")
const settlementDbPath = path.join(outputDir, "settlement.db")
const summaryPath = path.join(outputDir, "settlement-summary.json")

function queryJson(sql) {
  const out = execFileSync("sqlite3", ["-json", dbPath, sql], { encoding: "utf8" })
  return out.trim() ? JSON.parse(out) : []
}

function sqlString(value) {
  return "'" + String(value).replaceAll("'", "''") + "'"
}

function round3(value) {
  return Math.round((value + 1e-12) * 1000) / 1000
}

const rates = new Map()
for (const row of queryJson("SELECT account_id, rate_cents_per_kwh FROM account_rates")) {
  rates.set(row.account_id, row.rate_cents_per_kwh)
}

const credits = new Map()
for (const row of queryJson("SELECT district, credit_cents_per_kwh FROM district_credits")) {
  credits.set(row.district, row.credit_cents_per_kwh)
}

const normalized = fs.readFileSync(normalizedPath, "utf8")
  .split(/\r?\n/)
  .filter(line => line.trim())
  .map(line => JSON.parse(line))

const groups = new Map()
for (const row of normalized) {
  const key = `${row.account_id}\u0000${row.service_month}\u0000${row.district}`
  const current = groups.get(key) || {
    account_id: row.account_id,
    service_month: row.service_month,
    district: row.district,
    event_count: 0,
    adjusted_kwh: 0
  }
  current.event_count += 1
  current.adjusted_kwh += row.adjusted_kwh
  groups.set(key, current)
}

const accountMonths = Array.from(groups.values()).map(row => {
  const adjusted = round3(row.adjusted_kwh)
  const energy = Math.round(adjusted * rates.get(row.account_id))
  const credit = Math.round(adjusted * credits.get(row.district))
  return {
    account_id: row.account_id,
    service_month: row.service_month,
    district: row.district,
    event_count: row.event_count,
    adjusted_kwh: adjusted,
    energy_charge_cents: energy,
    district_credit_cents: credit,
    total_cents: energy - credit
  }
}).sort((a, b) => (
  a.service_month.localeCompare(b.service_month) ||
  a.account_id.localeCompare(b.account_id) ||
  a.district.localeCompare(b.district)
))

fs.mkdirSync(outputDir, { recursive: true })
if (fs.existsSync(settlementDbPath)) {
  fs.unlinkSync(settlementDbPath)
}

let sql = `
CREATE TABLE account_months (
  account_id TEXT NOT NULL,
  service_month TEXT NOT NULL,
  district TEXT NOT NULL,
  event_count INTEGER NOT NULL,
  adjusted_kwh REAL NOT NULL,
  energy_charge_cents INTEGER NOT NULL,
  district_credit_cents INTEGER NOT NULL,
  total_cents INTEGER NOT NULL,
  PRIMARY KEY (account_id, service_month, district)
);
`

for (const row of accountMonths) {
  sql += `INSERT INTO account_months VALUES (${[
    sqlString(row.account_id),
    sqlString(row.service_month),
    sqlString(row.district),
    row.event_count,
    row.adjusted_kwh.toFixed(3),
    row.energy_charge_cents,
    row.district_credit_cents,
    row.total_cents
  ].join(", ")});\n`
}

const sqlite = spawnSync("sqlite3", [settlementDbPath], { input: sql, encoding: "utf8" })
if (sqlite.status !== 0) {
  throw new Error(sqlite.stderr || "sqlite3 failed")
}

const districts = []
for (const district of [...new Set(accountMonths.map(row => row.district))].sort()) {
  const rows = accountMonths.filter(row => row.district === district)
  districts.push({
    district,
    account_month_count: rows.length,
    total_kwh: round3(rows.reduce((sum, row) => sum + row.adjusted_kwh, 0)),
    total_cents: rows.reduce((sum, row) => sum + row.total_cents, 0)
  })
}

const summary = {
  generated_from: "/app/output/normalized-events.jsonl",
  account_month_count: accountMonths.length,
  total_kwh: round3(accountMonths.reduce((sum, row) => sum + row.adjusted_kwh, 0)),
  total_cents: accountMonths.reduce((sum, row) => sum + row.total_cents, 0),
  districts
}

fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2) + "\n")
NODE
