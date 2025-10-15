# Testing Guide - Microservices API Gateway Assignment

## Quick Start (3 Steps)

1. **Start Docker Desktop** (ensure it's running)
2. **Build & Run**:
   ```powershell
   docker compose up --build
   ```
3. **Wait for**: `Kong started` message in logs

---

## Test Suite (Copy & Paste Ready)

### ✅ Test 1: Successful Request

```powershell
$headers = @{ "X-API-Key" = "DEMO-API-KEY-123"; "Content-Type" = "application/json" }
$body = @{ request_id = "req-1001"; query = "microservices gateway policy" } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/process-request -Method Post -Headers $headers -Body $body | ConvertTo-Json -Depth 6
```

**Expected**: HTTP 200, JSON response with `request_id`, `trace_id`, `summary`, `label`, `documents`

---

### ✅ Test 2: Idempotency (Duplicate request_id)

```powershell
# Send same request again immediately
Invoke-RestMethod -Uri http://localhost:8000/process-request -Method Post -Headers $headers -Body $body | ConvertTo-Json -Depth 6
```

**Expected**: Same response, returned instantly from cache. Check logs for `"phase":"cache_hit"`

---

### ✅ Test 3: Policy Denial (Forbidden Word)

```powershell
$denyBody = @{ request_id = "req-1002"; query = "this is a forbidden topic" } | ConvertTo-Json
try {
  Invoke-RestMethod -Uri http://localhost:8000/process-request -Method Post -Headers $headers -Body $denyBody
} catch {
  Write-Host "HTTP Status:" $_.Exception.Response.StatusCode.value__
  $_.ErrorDetails.Message | ConvertFrom-Json | ConvertTo-Json
}
```

**Expected**: HTTP 403, JSON with `"error": "denied"`, `"detail": "Query contains forbidden term"`

---

### ✅ Test 4: Rate Limiting (5 req/min)

```powershell
1..6 | ForEach-Object {
  $b = @{ request_id = "rate-$_"; query = "test $_" } | ConvertTo-Json
  try {
    $r = Invoke-WebRequest http://localhost:8000/process-request -Method Post -Headers $headers -Body $b
    Write-Host "$_ -> HTTP $($r.StatusCode) ✓"
  } catch {
    Write-Host "$_ -> HTTP $($_.Exception.Response.StatusCode.value__) (Rate Limited) ✗"
  }
}
```

**Expected**: First 5 succeed (200), 6th fails (429 Too Many Requests)

---

### ✅ Test 5: Missing API Key

```powershell
$noKey = @{ "Content-Type" = "application/json" }
try {
  Invoke-RestMethod -Uri http://localhost:8000/process-request -Method Post -Headers $noKey -Body $body
} catch {
  Write-Host "HTTP Status:" $_.Exception.Response.StatusCode.value__
}
```

**Expected**: HTTP 401 (Unauthorized)

---

### ✅ Test 6: Wrong Port (Should Fail)

```powershell
try {
  Invoke-RestMethod -Uri http://localhost:8001/process-request -Method Post -Headers $headers -Body $body
} catch {
  Write-Host "Error: no Route matched (port 8001 is admin API, use 8000)"
}
```

**Expected**: Error "no Route matched with those values"

---

## Inspect Audit Logs

```powershell
# View all logs
Get-Content .\logs\audit.jsonl

# Watch live
Get-Content .\logs\audit.jsonl -Wait

# Filter successful requests
Get-Content .\logs\audit.jsonl | Select-String success

# Filter denials
Get-Content .\logs\audit.jsonl | Select-String deny

# Filter cache hits (idempotency)
Get-Content .\logs\audit.jsonl | Select-String cache_hit
```

---

## Expected Log Entries

```jsonl
{"timestamp":1697347024.5,"phase":"success","request_id":"req-1001","trace_id":"req-1001-trace","status":"ok","http_status":200}
{"timestamp":1697347025.1,"phase":"cache_hit","request_id":"req-1001","trace_id":"req-1001-trace","status":"idempotent-return","http_status":200}
{"timestamp":1697347026.8,"phase":"deny","request_id":"req-1002","trace_id":"req-1002-trace","reason":"Query contains forbidden term","http_status":403}
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified` | Start Docker Desktop |
| `no Route matched with those values` | Use port 8000 (not 8001) |
| HTTP 401 Unauthorized | Add header: `X-API-Key: DEMO-API-KEY-123` |
| HTTP 403 Forbidden | Remove word "forbidden" from query |
| HTTP 429 Too Many Requests | Wait 60 seconds (rate limit reset) |
| Services not starting | Check `docker compose logs <service>` |

---

## Curl Commands (Linux/Mac/Git Bash)

### Successful Request
```bash
curl -X POST http://localhost:8000/process-request \
  -H "X-API-Key: DEMO-API-KEY-123" \
  -H "Content-Type: application/json" \
  -d '{"request_id":"req-1001","query":"microservices gateway policy"}'
```

### Policy Denial
```bash
curl -X POST http://localhost:8000/process-request \
  -H "X-API-Key: DEMO-API-KEY-123" \
  -H "Content-Type: application/json" \
  -d '{"request_id":"req-1002","query":"this is forbidden"}'
```

### Rate Limiting Test
```bash
for i in {1..6}; do
  curl -X POST http://localhost:8000/process-request \
    -H "X-API-Key: DEMO-API-KEY-123" \
    -H "Content-Type: application/json" \
    -d "{\"request_id\":\"rate-$i\",\"query\":\"test $i\"}" \
    -w "\nHTTP Status: %{http_code}\n\n"
done
```

---

## Verify All Components

```powershell
# Check Kong admin API
Invoke-RestMethod http://localhost:8001/services | ConvertTo-Json -Depth 4

# Check Kong plugins
Invoke-RestMethod http://localhost:8001/plugins | ConvertTo-Json -Depth 4

# Check service health endpoints (direct, bypassing gateway)
Invoke-RestMethod http://localhost:9001/health  # Policy
Invoke-RestMethod http://localhost:9002/health  # Retriever
Invoke-RestMethod http://localhost:9003/health  # Processor
```

---

## Assignment Deliverables Checklist

- [x] Kong API Gateway with routing, auth, rate limiting
- [x] Policy Service (denies "forbidden" queries)
- [x] Retriever Agent (POST /retrieve, top 3 docs)
- [x] Processor Agent (POST /process, summary + label)
- [x] Custom orchestration plugin (chain-plugin)
- [x] Idempotency (duplicate request_id cached)
- [x] Audit logging (logs/audit.jsonl with trace_id, request_id, status)
- [x] docker-compose.yml (single command deployment)
- [x] README.md (setup & run instructions)
- [x] Sample curl/PowerShell commands
- [x] Expected flow: Client → Gateway → Policy → Retriever → Processor

---

## Demo Script (2-3 min)

1. **Show Architecture** (30s)
   - Explain: Kong gateway → Policy → Retriever → Processor
   - Highlight: Auth, rate limiting, logging

2. **Run Successful Request** (30s)
   ```powershell
   # Execute Test 1
   # Show response with request_id, trace_id, summary, label
   ```

3. **Demonstrate Idempotency** (20s)
   ```powershell
   # Execute same request again
   # Point out instant response (cached)
   ```

4. **Show Policy Denial** (20s)
   ```powershell
   # Execute Test 3 with "forbidden"
   # Show HTTP 403 response
   ```

5. **Show Audit Logs** (30s)
   ```powershell
   Get-Content .\logs\audit.jsonl
   # Point out: timestamp, phase, request_id, trace_id, http_status
   ```

6. **Demonstrate Rate Limiting** (20s)
   ```powershell
   # Execute Test 4 (6 quick requests)
   # Show 6th request fails with 429
   ```

**Total**: ~2.5 minutes

---

## Cleanup

```powershell
docker compose down -v
```

---

## Submission Checklist

- [ ] Code pushed to repository
- [ ] README.md complete with setup instructions
- [ ] All tests verified working
- [ ] Audit logs generated (logs/audit.jsonl)
- [ ] Repository link shared via Google Drive
- [ ] (Optional) Demo video recorded

**Submission Deadline**: 17.10.2025
