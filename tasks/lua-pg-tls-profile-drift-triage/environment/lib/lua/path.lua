local M = {}

function M.read_all(path)
  local f = assert(io.open(path, "r"))
  local data = f:read("*a")
  f:close()
  return data
end

function M.write_all(path, data)
  local f = assert(io.open(path, "w"))
  f:write(data)
  f:close()
end

function M.split_lines(text)
  local lines = {}
  for line in (text .. "\n"):gmatch("(.-)\n") do
    lines[#lines + 1] = line
  end
  return lines
end

function M.dirname(path)
  return path:match("^(.*)/[^/]+$") or "."
end

function M.basename(path)
  return path:match("([^/]+)$") or path
end

return M
