local M = {}

function M.encode(value)
  local t = type(value)
  if t == "nil" then
    return "null"
  elseif t == "boolean" then
    return value and "true" or "false"
  elseif t == "number" then
    if value ~= value or value == math.huge or value == -math.huge then
      error("non-finite number")
    end
    return string.format("%.10g", value)
  elseif t == "string" then
    return M.encode_string(value)
  elseif t == "table" then
    if #value > 0 or next(value) == nil then
      return M.encode_array(value)
    end
    return M.encode_object(value)
  end
  error("unsupported type")
end

function M.encode_string(s)
  local escaped = s:gsub("\\", "\\\\"):gsub('"', '\\"'):gsub("\n", "\\n"):gsub("\r", "\\r")
  return '"' .. escaped .. '"'
end

function M.encode_array(arr)
  local parts = {}
  for i = 1, #arr do
    parts[#parts + 1] = M.encode(arr[i])
  end
  return "[" .. table.concat(parts, ",") .. "]"
end

function M.encode_object(obj)
  local keys = {}
  for k in pairs(obj) do
    if type(k) ~= "string" then
      error("object keys must be strings")
    end
    keys[#keys + 1] = k
  end
  table.sort(keys)
  local parts = {}
  for _, k in ipairs(keys) do
    parts[#parts + 1] = M.encode_string(k) .. ":" .. M.encode(obj[k])
  end
  return "{" .. table.concat(parts, ",") .. "}"
end

function M.decode(text)
  local pos = 1
  local function peek()
    return text:sub(pos, pos)
  end
  local function consume()
    pos = pos + 1
  end
  local function skip_ws()
    while true do
      local c = peek()
      if c == "" or not c:match("%s") then
        return
      end
      consume()
    end
  end
  local parse_value
  local function parse_string()
    consume()
    local start = pos
    local out = {}
    while true do
      local c = peek()
      if c == "" then
        error("unterminated string")
      end
      if c == '"' then
        consume()
        break
      end
      if c == "\\" then
        out[#out + 1] = text:sub(start, pos - 1)
        consume()
        local esc = peek()
        if esc == '"' or esc == "\\" or esc == "/" then
          out[#out + 1] = esc
          consume()
        elseif esc == "n" then
          out[#out + 1] = "\n"
          consume()
        elseif esc == "r" then
          out[#out + 1] = "\r"
          consume()
        else
          error("bad escape")
        end
        start = pos
      else
        consume()
      end
    end
    out[#out + 1] = text:sub(start, pos - 2)
    return table.concat(out)
  end
  local function parse_number()
    local start = pos
    while peek():match("[%d%+%-%e%.]") do
      consume()
    end
    return tonumber(text:sub(start, pos - 1))
  end
  local function parse_array()
    consume()
    skip_ws()
    local arr = {}
    if peek() == "]" then
      consume()
      return arr
    end
    while true do
      arr[#arr + 1] = parse_value()
      skip_ws()
      local c = peek()
      if c == "]" then
        consume()
        break
      end
      if c ~= "," then
        error("expected comma in array")
      end
      consume()
      skip_ws()
    end
    return arr
  end
  local function parse_object()
    consume()
    skip_ws()
    local obj = {}
    if peek() == "}" then
      consume()
      return obj
    end
    while true do
      skip_ws()
      if peek() ~= '"' then
        error("expected object key")
      end
      local key = parse_string()
      skip_ws()
      if peek() ~= ":" then
        error("expected colon")
      end
      consume()
      skip_ws()
      obj[key] = parse_value()
      skip_ws()
      local c = peek()
      if c == "}" then
        consume()
        break
      end
      if c ~= "," then
        error("expected comma in object")
      end
      consume()
    end
    return obj
  end
  function parse_value()
    skip_ws()
    local c = peek()
    if c == '"' then
      return parse_string()
    elseif c == "{" then
      return parse_object()
    elseif c == "[" then
      return parse_array()
    elseif c == "t" then
      if text:sub(pos, pos + 3) == "true" then
        pos = pos + 4
        return true
      end
      error("bad literal")
    elseif c == "f" then
      if text:sub(pos, pos + 4) == "false" then
        pos = pos + 5
        return false
      end
      error("bad literal")
    elseif c == "n" then
      if text:sub(pos, pos + 3) == "null" then
        pos = pos + 4
        return nil
      end
      error("bad literal")
    else
      return parse_number()
    end
  end
  local value = parse_value()
  skip_ws()
  if pos <= #text then
    error("trailing json")
  end
  return value
end

return M
