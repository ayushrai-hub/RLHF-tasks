local M = {}

function M.drop_revoked(rows, revoked)
  local out = {}
  for _, row in ipairs(rows) do
    if not revoked[row.serial] then
      out[#out + 1] = row
    end
  end
  return out
end

return M
