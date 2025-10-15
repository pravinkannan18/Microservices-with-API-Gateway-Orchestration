# Microservices with Kong API Gateway – Setup & Test Guide

This project demonstrates a 3-microservice architecture (Policy, Retriever, Processor) managed by Kong API Gateway with authentication, rate limiting, orchestration, and audit logging.

---

## Prerequisites

- Docker Desktop (running)
- Docker Compose v2+
- PowerShell (Windows) or bash (Linux/Mac)

---

## Setup & Run

1. **Start Docker Desktop** and ensure it is running.
2. **From the project root, build and start all services:**
   ```powershell
   docker compose up --build
   ```
   Wait for `Kong started` and all services to show "Uvicorn running...".

3. **(Optional) Run in background:**
   ```powershell
   docker compose up --build -d
   ```

4. **Check all services are up:**
   ```powershell
   docker compose ps
   ```

---

## Sample curl Commands

### 1. Successful Orchestration Request

```bash
curl -X POST http://localhost:8000/process-request \
  -H "X-API-Key: DEMO-API-KEY-123" \
  -H "Content-Type: application/json" \
  -d '{"request_id":"req-1001","query":"microservices gateway policy"}'
```

### 2. Idempotency (Repeat Same request_id)

```bash
curl -X POST http://localhost:8000/process-request \
  -H "X-API-Key: DEMO-API-KEY-123" \
  -H "Content-Type: application/json" \
  -d '{"request_id":"req-1001","query":"microservices gateway policy"}'
```

### 3. Policy Denial (Forbidden Word)

```bash
curl -X POST http://localhost:8000/process-request \
  -H "X-API-Key: DEMO-API-KEY-123" \
  -H "Content-Type: application/json" \
  -d '{"request_id":"req-1002","query":"this is forbidden"}'
```

### 4. Rate Limiting (6 Requests in a Minute)

```bash
for i in {1..6}; do
  curl -X POST http://localhost:8000/process-request \
    -H "X-API-Key: DEMO-API-KEY-123" \
    -H "Content-Type: application/json" \
    -d "{\"request_id\":\"rate-$i\",\"query\":\"test $i\"}"
done
```

### 5. Missing API Key (Should Fail)

```bash
curl -X POST http://localhost:8000/process-request \
  -H "Content-Type: application/json" \
  -d '{"request_id":"req-1003","query":"test"}'
```

---

## Log Inspection

All requests are logged to `logs/audit.jsonl`.

```powershell
Get-Content .\logs\audit.jsonl
```

Each line: `{ "timestamp": ..., "phase": "success|error|deny|cache_hit", "request_id": ..., "trace_id": ..., "status": ..., "http_status": ... }`

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `no Route matched with those values` | Use port 8000, POST method, correct path `/process-request` |
| HTTP 401 Unauthorized | Add header: `X-API-Key: DEMO-API-KEY-123` |
| HTTP 403 Forbidden | Remove word "forbidden" from query |
| HTTP 429 Too Many Requests | Wait 60 seconds (rate limit reset) |
| Docker error: pipe not found | Start Docker Desktop |

---

## Cleanup

```powershell
docker compose down -v
```

---

## License

MIT (educational demonstration)
