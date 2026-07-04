local M = {}

local function parse_date(text)
  local y, m, d = text:match("^(%d%d%d%d)-(%d%d)-(%d%d)$")
  return os.time({ year = tonumber(y), month = tonumber(m), day = tonumber(d), hour = 12 })
end

function M.active_window(row, reference_clock, grace_days)
  grace_days = grace_days or 0
  local ref_ts = parse_date(reference_clock)
  local end_ts = parse_date(row.not_after)
  return end_ts >= ref_ts - (grace_days * 86400)
end

return M
