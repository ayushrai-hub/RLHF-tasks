local M = {}

function M.run_capture(cmd)
  local tmp = os.tmpname()
  local full = string.format("%s > %q 2>&1", cmd, tmp)
  local ok = os.execute(full)
  local f = io.open(tmp, "r")
  local out = f and f:read("*a") or ""
  if f then
    f:close()
  end
  os.remove(tmp)
  if not ok then
    error(out)
  end
  return out
end

function M.psql_rows(sql)
  local quoted = sql:gsub("'", "'\\''")
  local cmd = string.format(
    "bash -lc 'runuser -u postgres -- psql -d payments_tls -t -A -F \"|\" -c %q'",
    quoted
  )
  local out = M.run_capture(cmd)
  local rows = {}
  for line in out:gmatch("[^\r\n]+") do
    if line ~= "" then
      local cols = {}
      for part in (line .. "|"):gmatch("(.-)|") do
        cols[#cols + 1] = part
      end
      rows[#rows + 1] = cols
    end
  end
  return rows
end

function M.load_yaml_json(path)
  local quoted = path:gsub("'", "'\\''")
  local cmd = string.format(
    "python3 -c \"import json, yaml, sys; print(json.dumps(yaml.safe_load(open(sys.argv[1]))))\" %q",
    quoted
  )
  local out = M.run_capture(cmd)
  local json = require("lib.lua.json")
  return json.decode(out)
end

function M.load_toml_json(path)
  local quoted = path:gsub("'", "'\\''")
  local cmd = string.format(
    "python3 -c \"import json, tomllib, sys; print(json.dumps(tomllib.load(open(sys.argv[1],'rb'))))\" %q",
    quoted
  )
  local out = M.run_capture(cmd)
  local json = require("lib.lua.json")
  return json.decode(out)
end

function M.sha256_hex(body)
  local tmp = os.tmpname()
  local f = assert(io.open(tmp, "w"))
  f:write(body)
  f:close()
  local out = M.run_capture(string.format("sha256sum %q | awk '{print $1}'", tmp))
  os.remove(tmp)
  return out:gsub("%s+", "")
end

return M
