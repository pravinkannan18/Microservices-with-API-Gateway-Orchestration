local ChainPlugin = {
  PRIORITY = 800,
  VERSION = "0.2.0",
}

local http = require "resty.http"
local cjson = require "cjson.safe"
local ngx_now = ngx.now
local fmt = string.format

-- simple in-worker cache (not shared across workers) for idempotency
local cache = {}

local function log_event(conf, phase, data)
  if not conf.log_path then return end
  local file, err = io.open(conf.log_path, "a")
  if not file then
    kong.log.err("failed to open log file: ", err)
    return
  end
  data.timestamp = ngx_now()
  data.phase = phase
  file:write(cjson.encode(data) .. "\n")
  file:close()
end

local function request_json(httpc, url, body_tbl)
  local res, err = httpc:request_uri(url, {
    method = "POST",
    body = cjson.encode(body_tbl),
    headers = { ["Content-Type"] = "application/json" }
  })
  if not res then return nil, err end
  local decoded = cjson.decode(res.body) or {}
  return { status = res.status, body = decoded }, nil
end

function ChainPlugin:access(conf)
  if kong.request.get_path() ~= "/process-request" then
    return
  end

  local raw_body = kong.request.get_raw_body()
  local body = cjson.decode(raw_body or "{}") or {}
  local request_id = body.request_id or kong.request.get_header("x-request-id") or tostring(math.random(1,1e9))
  local query = body.query or ""
  local trace_id = kong.request.get_header("x-trace-id") or request_id .. "-trace"

  -- idempotency check
  local entry = cache[request_id]
  if entry and (ngx_now() - entry.ts) < (conf.idempotency_ttl or 300) then
    kong.response.set_header("X-Trace-Id", trace_id)
    kong.response.set_header("X-Request-Id", request_id)
    log_event(conf, "cache_hit", { trace_id = trace_id, request_id = request_id, status = "idempotent-return", http_status = 200 })
    return kong.response.exit(200, entry.payload)
  end

  local httpc = http.new(); httpc:set_timeout(3000)

  -- 1. Policy
  local policy_url = fmt("http://%s:9000/policy", conf.policy_service)
  local policy_res, err = request_json(httpc, policy_url, { request_id = request_id, query = query })
  if not policy_res then
    log_event(conf, "error", { step = "policy", error = err, request_id = request_id, trace_id = trace_id, http_status = 500 })
    return kong.response.exit(500, { error = "policy call failed" })
  end
  if policy_res.body.policy == "deny" then
    log_event(conf, "deny", { request_id = request_id, trace_id = trace_id, reason = policy_res.body.detail, http_status = 403 })
    return kong.response.exit(403, { request_id = request_id, trace_id = trace_id, error = "denied", detail = policy_res.body.detail })
  end

  -- 2. Retriever
  local retr_url = fmt("http://%s:9000/retrieve", conf.retriever_service)
  local retr_res, err = request_json(httpc, retr_url, { request_id = request_id, query = query })
  if not retr_res then
    log_event(conf, "error", { step = "retriever", error = err, request_id = request_id, trace_id = trace_id, http_status = 500 })
    return kong.response.exit(500, { error = "retriever call failed" })
  end

  -- 3. Processor
  local proc_url = fmt("http://%s:9000/process", conf.processor_service)
  local proc_res, err = request_json(httpc, proc_url, { request_id = request_id, query = query, documents = retr_res.body.documents or {} })
  if not proc_res then
    log_event(conf, "error", { step = "processor", error = err, request_id = request_id, trace_id = trace_id, http_status = 500 })
    return kong.response.exit(500, { error = "processor call failed" })
  end

  local payload = {
    request_id = request_id,
    trace_id = trace_id,
    summary = proc_res.body.summary,
    label = proc_res.body.label,
    documents = retr_res.body.documents or {},
  }

  cache[request_id] = { ts = ngx_now(), payload = payload }

  kong.response.set_header("X-Trace-Id", trace_id)
  kong.response.set_header("X-Request-Id", request_id)
  log_event(conf, "success", { request_id = request_id, trace_id = trace_id, status = "ok", http_status = 200 })
  return kong.response.exit(200, payload)
end

return ChainPlugin