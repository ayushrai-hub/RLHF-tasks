#!/usr/bin/env bash
set -euo pipefail

cat > "/app/environment/pkg/p48/query.lua" <<'LUA'
local shell = require("lib.lua.shell")

local M = {}

function M.fetch_rows()
  local sql = [[
    SELECT ci.serial, ci.subject_cn, ci.sha256_hex, ci.not_before, ci.not_after, ci.role_tag
    FROM cert_inventory ci
    LEFT JOIN revocation_events re ON re.serial = ci.serial
    WHERE re.serial IS NULL
    ORDER BY ci.serial
  ]]
  local raw = shell.psql_rows(sql)
  local rows = {}
  for _, cols in ipairs(raw) do
    rows[#rows + 1] = {
      serial = cols[1],
      subject_cn = cols[2],
      sha256_hex = cols[3],
      not_before = cols[4],
      not_after = cols[5],
      role_tag = cols[6],
    }
  end
  return rows
end

return M
LUA

cat > "/app/environment/lib/lua/fpcanon.lua" <<'LUA'
local M = {}

function M.canonical_fp(raw)
  if not raw or raw == "" then
    return ""
  end
  local body = string.lower(raw:gsub(":", ""))
  local parts = {}
  for i = 1, #body, 2 do
    parts[#parts + 1] = body:sub(i, i + 1)
  end
  return table.concat(parts, ":")
end

return M
LUA

cat > "/app/environment/lib/lua/grace.lua" <<'LUA'
local M = {}

local function parse_date(text)
  local y, m, d = text:match("^(%d%d%d%d)-(%d%d)-(%d%d)$")
  return os.time({ year = tonumber(y), month = tonumber(m), day = tonumber(d), hour = 12 })
end

function M.active_window(row, reference_clock, grace_days)
  grace_days = grace_days or 14
  local ref_ts = parse_date(reference_clock)
  local end_ts = parse_date(row.not_after)
  return end_ts >= ref_ts - (grace_days * 86400)
end

return M
LUA

cat > "/app/environment/pkg/c91/merge.lua" <<'LUA'
local shell = require("lib.lua.shell")

local M = {}

function M.merge_profiles(yaml_doc, _toml_doc)
  local merged = {}
  for _, anchor in ipairs(yaml_doc.trust_anchors or {}) do
    merged[#merged + 1] = anchor
  end
  return merged
end

function M.client_ca_map(toml_doc)
  local out = {}
  local block = toml_doc.client_ca or {}
  for service, body in pairs(block) do
    out[service] = body.role_tag
  end
  return out
end

function M.load_yaml(path)
  return shell.load_yaml_json(path)
end

function M.load_toml(path)
  return shell.load_toml_json(path)
end

return M
LUA

cat > "/app/environment/pkg/r63/publish.lua" <<'LUA'
local M = {}

function M.build_manifest(yaml_doc, yaml_anchors, fp_index, revoked_fps, inventory_all_fps, service_rows, digest, normalize)
  local trust = {}
  for _, anchor in ipairs(yaml_anchors) do
    local cfg_fp = normalize.canonical_fp(anchor.fingerprint)
    local enabled = false
    local reason = "stale_config"
    if revoked_fps[cfg_fp] then
      reason = "revoked"
    elseif fp_index[cfg_fp] then
      enabled = true
      reason = "inventory_match"
    elseif inventory_all_fps[cfg_fp] and not fp_index[cfg_fp] then
      reason = "expired"
    end
    trust[#trust + 1] = {
      anchor_id = anchor.anchor_id,
      fingerprint = cfg_fp,
      enabled = enabled,
      reason = reason,
    }
  end
  table.sort(trust, function(a, b)
    return a.anchor_id < b.anchor_id
  end)

  local drift_staging = {}
  for _, anchor in ipairs(yaml_anchors) do
    local cfg_fp = normalize.canonical_fp(anchor.fingerprint)
    if inventory_all_fps[cfg_fp] and anchor.fingerprint ~= cfg_fp then
      drift_staging[#drift_staging + 1] = {
        anchor.anchor_id,
        {
          source = "yaml",
          field = "fingerprint",
          config_value = anchor.fingerprint,
          inventory_value = cfg_fp,
        },
      }
    end
  end
  table.sort(drift_staging, function(a, b)
    if a[1] == b[1] then
      return a[2].field < b[2].field
    end
    return a[1] < b[1]
  end)
  local drift = {}
  for _, item in ipairs(drift_staging) do
    drift[#drift + 1] = item[2]
  end

  return {
    api_version = yaml_doc.api_version,
    rollover_epoch = yaml_doc.rollover_epoch,
    inventory_digest = digest,
    trust_anchors = trust,
    service_bindings = service_rows,
    drift_rows = drift,
  }
end

return M
LUA

cat > "/app/environment/exec/driver.lua" <<'LUA'
local json = require("lib.lua.json")
local path = require("lib.lua.path")
local query = require("pkg.p48.query")
local normalize = require("lib.lua.fpcanon")
local expiry = require("lib.lua.grace")
local bundle = require("pkg.c91.merge")
local publish = require("pkg.r63.publish")
local shell = require("lib.lua.shell")

local M = {}

local function revoked_serials()
  local rows = shell.psql_rows("SELECT serial FROM revocation_events")
  local out = {}
  for _, cols in ipairs(rows) do
    out[cols[1]] = true
  end
  return out
end

local function all_inventory_fps()
  local rows = shell.psql_rows("SELECT sha256_hex FROM cert_inventory")
  local out = {}
  for _, cols in ipairs(rows) do
    local fp = normalize.canonical_fp(cols[1])
    out[fp] = true
  end
  return out
end

local function revoked_fps()
  local rows = shell.psql_rows(
    "SELECT ci.sha256_hex FROM revocation_events re JOIN cert_inventory ci ON ci.serial = re.serial"
  )
  local out = {}
  for _, cols in ipairs(rows) do
    out[normalize.canonical_fp(cols[1])] = true
  end
  return out
end

local function by_serial_index(rows)
  local out = {}
  for _, row in ipairs(rows) do
    out[row.serial] = row
  end
  return out
end

local function role_binding_rows()
  return shell.psql_rows(
    "SELECT service_name, role_tag, client_ca_serial FROM role_bindings ORDER BY service_name"
  )
end

function M.run(cfg)
  local yaml_doc = bundle.load_yaml(cfg.yaml_bundle)
  local toml_doc = bundle.load_toml(cfg.toml_bundle)
  local reference_clock = yaml_doc.reference_clock or cfg.reference_clock
  local grace_days = cfg.grace_days or 14

  local raw_rows = query.fetch_rows()
  local active = {}
  for _, row in ipairs(raw_rows) do
    if expiry.active_window(row, reference_clock, grace_days) then
      row.fingerprint = normalize.canonical_fp(row.sha256_hex)
      active[#active + 1] = row
    end
  end

  local fp_index = {}
  for _, row in ipairs(active) do
    fp_index[row.fingerprint] = row
  end

  local digest_lines = {}
  for _, row in ipairs(active) do
    digest_lines[#digest_lines + 1] = row.serial .. ":" .. row.fingerprint
  end
  table.sort(digest_lines)
  local digest = shell.sha256_hex(table.concat(digest_lines, "\n"))

  local yaml_anchors = bundle.merge_profiles(yaml_doc, toml_doc)
  local client_map = bundle.client_ca_map(toml_doc)
  local inventory_by_serial = by_serial_index(active)
  local binding_rows = role_binding_rows()

  local service_rows = {}
  for service, _role_tag in pairs(client_map) do
    local bound_serial = nil
    for _, cols in ipairs(binding_rows) do
      if cols[1] == service then
        bound_serial = cols[3]
        break
      end
    end
    local inv = bound_serial and inventory_by_serial[bound_serial] or nil
    if inv then
      service_rows[#service_rows + 1] = {
        service = service,
        client_ca = inv.subject_cn,
        fingerprint = inv.fingerprint,
      }
    end
  end
  table.sort(service_rows, function(a, b)
    return a.service < b.service
  end)

  return publish.build_manifest(
    yaml_doc,
    yaml_anchors,
    fp_index,
    revoked_fps(),
    all_inventory_fps(),
    service_rows,
    digest,
    normalize
  )
end

function M.write_report(report, out_path)
  path.write_all(out_path, json.encode(report) .. "\n")
end

return M
LUA

bash /app/environment/ci/install_cli.sh
bash /app/environment/ci/seed_inventory.sh
/app/bin/ingressctl tls-reconcile
