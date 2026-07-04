local shell = require("lib.lua.shell")

local M = {}

local function collect_toml_anchors(toml_doc)
  local anchors = {}
  local block = toml_doc.trust_anchors or {}
  for anchor_id, body in pairs(block) do
    anchors[#anchors + 1] = {
      anchor_id = anchor_id,
      fingerprint = body.fingerprint,
      enabled = body.enabled,
    }
  end
  return anchors
end

function M.merge_profiles(yaml_doc, toml_doc)
  local merged = {}
  local seen = {}
  for _, anchor in ipairs(yaml_doc.trust_anchors or {}) do
    merged[#merged + 1] = anchor
    seen[anchor.anchor_id] = true
  end
  for _, anchor in ipairs(collect_toml_anchors(toml_doc)) do
    if not seen[anchor.anchor_id] then
      merged[#merged + 1] = anchor
      seen[anchor.anchor_id] = true
    else
      for i, row in ipairs(merged) do
        if row.anchor_id == anchor.anchor_id then
          merged[i] = anchor
        end
      end
    end
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
