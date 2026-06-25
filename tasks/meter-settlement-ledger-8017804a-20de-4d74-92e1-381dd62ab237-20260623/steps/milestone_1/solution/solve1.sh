#!/bin/bash
set -euo pipefail

node <<'NODE'
const fs = require("fs")
const path = require("path")
const { execFileSync } = require("child_process")

const appDir = "/app"
const rawDir = path.join(appDir, "raw-events")
const dbPath = path.join(appDir, "catalog", "meter_catalog.db")
const outputDir = path.join(appDir, "output")
const outputPath = path.join(outputDir, "normalized-events.jsonl")

function queryJson(sql) {
  const out = execFileSync("sqlite3", ["-json", dbPath, sql], { encoding: "utf8" })
  return out.trim() ? JSON.parse(out) : []
}

function round3(value) {
  return Math.round((value + 1e-12) * 1000) / 1000
}

const meters = new Map()
for (const row of queryJson("SELECT meter_id, account_id, district, multiplier, active_from, active_to FROM meters")) {
  meters.set(row.meter_id, row)
}

const chosen = new Map()
for (const file of fs.readdirSync(rawDir).filter(name => name.endsWith(".jsonl")).sort()) {
  const content = fs.readFileSync(path.join(rawDir, file), "utf8")
  for (const line of content.split(/\r?\n/)) {
    if (!line.trim()) {
      continue
    }
    const event = JSON.parse(line)
    const current = chosen.get(event.event_id)
    if (
      !current ||
      event.revision > current.revision ||
      (event.revision === current.revision && event.source_priority > current.source_priority)
    ) {
      chosen.set(event.event_id, event)
    }
  }
}

const rows = []
for (const event of chosen.values()) {
  const meter = meters.get(event.meter_id)
  if (event.quality !== "valid" || !meter) {
    continue
  }
  if (event.observed_at < meter.active_from) {
    continue
  }
  if (meter.active_to && event.observed_at >= meter.active_to) {
    continue
  }
  rows.push({
    event_id: event.event_id,
    observed_at: event.observed_at,
    account_id: meter.account_id,
    meter_id: event.meter_id,
    service_month: event.observed_at.slice(0, 7),
    district: meter.district,
    adjusted_kwh: round3(event.kwh * meter.multiplier),
    source_quality: event.quality
  })
}

rows.sort((a, b) => (
  a.service_month.localeCompare(b.service_month) ||
  a.account_id.localeCompare(b.account_id) ||
  a.observed_at.localeCompare(b.observed_at) ||
  a.event_id.localeCompare(b.event_id)
))

fs.mkdirSync(outputDir, { recursive: true })
fs.writeFileSync(outputPath, rows.map(row => JSON.stringify(row)).join("\n") + "\n")
NODE
