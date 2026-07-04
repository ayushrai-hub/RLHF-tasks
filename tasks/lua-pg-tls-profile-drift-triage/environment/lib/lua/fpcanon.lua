local M = {}

function M.canonical_fp(raw)
  if not raw or raw == "" then
    return ""
  end
  return string.upper(raw)
end

return M
