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

function newerEvent(candidate, current) {
  if (candidate.revision !== current.revision) {
    return candidate.revision > current.revision
  }
  if (candidate.source_priority !== current.source_priority) {
    return candidate.source_priority > current.source_priority
  }
  return (candidate.received_at || "") > (current.received_at || "")
}

const meters = new Map()
for (const row of queryJson("SELECT meter_id, account_id, district, multiplier, active_from, active_to FROM meters")) {
  meters.set(row.meter_id, row)
}

const billingWindows = new Map()
for (const row of queryJson("SELECT district, utc_offset_hours, cutover_day, cutover_hour FROM district_billing_windows")) {
  billingWindows.set(row.district, row)
}

const peakWindows = new Map()
for (const row of queryJson("SELECT district, peak_start_hour, peak_end_hour FROM district_peak_windows")) {
  peakWindows.set(row.district, row)
}

const holidays = new Set()
for (const row of queryJson("SELECT district, local_date FROM district_holidays")) {
  holidays.add(`${row.district}\u0000${row.local_date}`)
}

const registerBaselines = new Map()
for (const row of queryJson("SELECT meter_id, baseline_register_kwh, rollover_kwh FROM meter_register_baselines")) {
  registerBaselines.set(row.meter_id, {
    previous: Number(row.baseline_register_kwh),
    rollover: Number(row.rollover_kwh)
  })
}

function formatMonth(year, monthIndex) {
  return `${year}-${String(monthIndex + 1).padStart(2, "0")}`
}

function previousMonth(year, monthIndex) {
  if (monthIndex === 0) {
    return [year - 1, 11]
  }
  return [year, monthIndex - 1]
}

function serviceMonth(observedAt, district) {
  const window = billingWindows.get(district)
  if (!window) {
    return observedAt.slice(0, 7)
  }
  const local = new Date(new Date(observedAt).getTime() + Number(window.utc_offset_hours) * 60 * 60 * 1000)
  let year = local.getUTCFullYear()
  let monthIndex = local.getUTCMonth()
  const day = local.getUTCDate()
  const hour = local.getUTCHours()
  if (day < window.cutover_day || (day === window.cutover_day && hour < window.cutover_hour)) {
    ;[year, monthIndex] = previousMonth(year, monthIndex)
  }
  return formatMonth(year, monthIndex)
}

function localDateParts(observedAt, district) {
  const window = billingWindows.get(district)
  const offsetHours = window ? Number(window.utc_offset_hours) : 0
  const local = new Date(new Date(observedAt).getTime() + offsetHours * 60 * 60 * 1000)
  const year = local.getUTCFullYear()
  const month = String(local.getUTCMonth() + 1).padStart(2, "0")
  const day = String(local.getUTCDate()).padStart(2, "0")
  return {
    date: `${year}-${month}-${day}`,
    hour: local.getUTCHours(),
    dayOfWeek: local.getUTCDay()
  }
}

function billingBand(observedAt, district) {
  const peak = peakWindows.get(district)
  if (!peak) {
    return "standard"
  }
  const local = localDateParts(observedAt, district)
  if (local.dayOfWeek === 0 || local.dayOfWeek === 6) {
    return "standard"
  }
  if (holidays.has(`${district}\u0000${local.date}`)) {
    return "standard"
  }
  return local.hour >= Number(peak.peak_start_hour) && local.hour < Number(peak.peak_end_hour)
    ? "peak"
    : "standard"
}

function intervalKwh(event) {
  if (event.reading_type !== "register") {
    return Number(event.kwh)
  }
  const state = registerBaselines.get(event.meter_id)
  if (!state) {
    throw new Error(`missing register baseline for ${event.meter_id}`)
  }
  const current = Number(event.register_kwh)
  const delta = current >= state.previous
    ? current - state.previous
    : current + state.rollover - state.previous
  state.previous = current
  return delta
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
    if (!current || newerEvent(event, current)) {
      chosen.set(event.event_id, event)
    }
  }
}

const accepted = []
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
  accepted.push({ event, meter })
}

accepted.sort((a, b) => (
  a.event.meter_id.localeCompare(b.event.meter_id) ||
  a.event.observed_at.localeCompare(b.event.observed_at) ||
  a.event.event_id.localeCompare(b.event.event_id)
))

const rows = []
for (const { event, meter } of accepted) {
  rows.push({
    event_id: event.event_id,
    observed_at: event.observed_at,
    account_id: meter.account_id,
    meter_id: event.meter_id,
    service_month: serviceMonth(event.observed_at, meter.district),
    district: meter.district,
    adjusted_kwh: round3(intervalKwh(event) * meter.multiplier),
    source_quality: event.quality,
    billing_band: billingBand(event.observed_at, meter.district)
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
