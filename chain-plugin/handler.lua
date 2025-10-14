local ChainPlugin = {
  PRIORITY = 800,
  VERSION = "0.1.0",
}

local http = require "resty.http"
local cjson = require "cjson.safe"

local function log_event(conf, phase, data)
  if not conf.log_path then
    return
  end
  local file, err = io.open(conf.log_path, "a")
  if not file then
    kong.log.err("failed to open log file: ", err)
    return
  end
  data.timestamp = ngx.now()
  data.phase = phase
  file:write(cjson.encode(data) .. "\n")
  file:close()
end

function ChainPlugin:access(conf)
  -- Only perform chain when hitting processor route
  local chain = conf.chain or {}
  if #chain == 0 then
    return
  end
  local aggregated = {}
  for _, svc in ipairs(chain) do
    local httpc = http.new()
    httpc:set_timeout(2000)
    local url = string.format("http://%s:9000/%s", svc, svc)
    local res, err = httpc:request_uri(url, { method = "GET" })
    if not res then
      kong.log.err("chain call failed for ", svc, ": ", err)
      table.insert(aggregated, { service = svc, error = err })
    else
      table.insert(aggregated, { service = svc, status = res.status, body = res.body })
    end
  end
  kong.ctx.shared.chain_results = aggregated
  log_event(conf, "access", { request_id = kong.request.get_header("x-request-id"), chain = aggregated })
end

function ChainPlugin:header_filter(conf)
  if kong.ctx.shared.chain_results then
    kong.response.set_header("X-Chain-Results", cjson.encode(kong.ctx.shared.chain_results))
  end
end

return ChainPlugin