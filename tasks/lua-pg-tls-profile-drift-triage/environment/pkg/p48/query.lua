local shell = require("lib.lua.shell")

local M = {}

function M.fetch_rows()
  local sql = [[
    SELECT serial, subject_cn, fingerprint_md5, not_before, not_after, role_tag
    FROM cert_inventory
    ORDER BY serial
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
