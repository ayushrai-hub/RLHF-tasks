local M = {}

function M.build_manifest(yaml_doc, anchors, inventory, service_rows, digest)
  local trust = {}
  for _, anchor in ipairs(anchors) do
    trust[#trust + 1] = {
      anchor_id = anchor.anchor_id,
      fingerprint = anchor.fingerprint,
      enabled = anchor.enabled ~= false,
      reason = anchor.enabled and "inventory_match" or "stale_config",
    }
  end
  table.sort(trust, function(a, b)
    return a.anchor_id < b.anchor_id
  end)
  local bindings = {}
  for _, row in ipairs(service_rows) do
    bindings[#bindings + 1] = row
  end
  return {
    api_version = yaml_doc.api_version,
    rollover_epoch = yaml_doc.rollover_epoch,
    inventory_digest = digest,
    trust_anchors = trust,
    service_bindings = bindings,
    drift_rows = {},
  }
end

return M
