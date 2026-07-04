local M = {}

function M.to_hex(bytes)
  return string.format("%x", tonumber(bytes) or 0)
end

return M
