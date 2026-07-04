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

local function role_index(rows)
  local by_role = {}
  for _, row in ipairs(rows) do
    by_role[row.role_tag] = row
  end
  return by_role
end

function M.run(cfg)
  local yaml_doc = bundle.load_yaml(cfg.yaml_bundle)
  local toml_doc = bundle.load_toml(cfg.toml_bundle)
  local reference_clock = yaml_doc.reference_clock or cfg.reference_clock
  local grace_days = cfg.grace_days or 14

  local raw_rows = query.fetch_rows()
  local revoked = revoked_serials()
  local active = {}
  for _, row in ipairs(raw_rows) do
    if not revoked[row.serial] and expiry.active_window(row, reference_clock, grace_days) then
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

  local merged_anchors = bundle.merge_profiles(yaml_doc, toml_doc)
  local client_map = bundle.client_ca_map(toml_doc)
  local bindings_by_role = role_index(active)

  local service_rows = {}
  for service, role_tag in pairs(client_map) do
    local inv = bindings_by_role[role_tag]
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

  return publish.build_manifest(yaml_doc, merged_anchors, active, service_rows, digest)
end

function M.write_report(report, out_path)
  path.write_all(out_path, json.encode(report) .. "\n")
end

return M
