# Microservices Behind an API Gateway (Assignment Implementation)

Implements a 3‑microservice architecture (Policy, Retriever, Processor) fronted by **Kong API Gateway** with a **custom orchestration plugin** that performs request governance, chaining, idempotency, authentication, rate limiting, and structured JSON logging.

Submission Date Target: 17.10.2025

## High-Level Flow

Client -> (API Key + rate limit enforced) -> `POST /process-request` (Gateway Route)
1. Gateway plugin extracts: `request_id`, `query` and assigns/propagates `trace_id`.
2. Calls Policy Service (`POST /policy`) – denies if `query` contains the word `forbidden`.
3. Calls Retriever Service (`POST /retrieve`) – returns top 3 lexical matches from a small in‑container dataset.
4. Calls Processor Service (`POST /process`) – summarizes retrieved docs and assigns a label.
5. Combines results and returns `{ request_id, trace_id, summary, label, documents }`.
6. Duplicate `request_id` within TTL returns cached response (idempotent behavior).

All steps are logged to `logs/audit.jsonl` with: `timestamp, phase, request_id, trace_id, status/http_status` and step markers.

## Components

| Component | Purpose |
|-----------|---------|
| Kong Gateway | Routing, key-auth, rate limiting (5 req/min), custom orchestration plugin |
| chain-plugin | Lua plugin orchestrating policy -> retriever -> processor, idempotency cache, logging |
| Policy Service | Validates query; denies if contains `forbidden` (case-insensitive) |
| Retriever Service | Scores dataset docs vs query; returns top 3 matches |
| Processor Service | Summarizes documents and assigns heuristic label |
| audit.jsonl | Persistent JSON lines log (mounted volume) |

## Security & Governance

Authentication: Kong `key-auth` (API key via `X-API-Key` header).
Rate Limiting: 5 requests per minute (local policy) on the orchestration route.
Idempotency: Cache keyed by `request_id` with configurable TTL (`idempotency_ttl`, default 300s) inside plugin worker.

## Endpoints (Internal Microservices)

| Service | Endpoint | Method | Body |
|---------|----------|--------|------|
| Policy | `/policy` | POST | `{ request_id, query }` |
| Retriever | `/retrieve` | POST | `{ request_id, query }` |
| Processor | `/process` | POST | `{ request_id, query, documents:[...] }` |

## Gateway Public Endpoint

`POST http://localhost:8000/process-request`

Body:
```json
{ "request_id": "12345", "query": "microservices policy gateway" }
```

Headers required:
```
X-API-Key: DEMO-API-KEY-123
```

Optional tracing headers accepted: `X-Trace-Id`, `X-Request-Id` (otherwise generated/derived).

## Directory Structure

```
├── docker-compose.yml
├── kong.conf
├── kong.yml
├── chain-plugin/
│   ├── handler.lua
│   └── schema.lua
├── policy/
│   ├── Dockerfile
│   └── app.py
├── retriever/
│   ├── Dockerfile
│   ├── app.py
│   └── dataset.json
├── processor/
│   ├── Dockerfile
│   └── app.py
├── logs/
│   └── audit.jsonl
└── README.md
```

## Run Locally

```powershell
docker compose up --build
```

Wait for: `Kong started`.

## Sample Requests (PowerShell)

Successful request:
```powershell
$body = @{ request_id = "req-001"; query = "microservices gateway policy" } | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/process-request `
  -Headers @{ 'X-API-Key'='DEMO-API-KEY-123' } `
  -Body $body `
  -ContentType 'application/json' | ConvertTo-Json -Depth 6
```

Idempotent repeat (same request_id returns identical result immediately):
```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/process-request `
  -Headers @{ 'X-API-Key'='DEMO-API-KEY-123' } `
  -Body $body -ContentType 'application/json' | ConvertTo-Json -Depth 6
```

Policy denial example:
```powershell
$denyBody = @{ request_id = "req-002"; query = "this contains forbidden term" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/process-request `
  -Headers @{ 'X-API-Key'='DEMO-API-KEY-123' } `
  -Body $denyBody -ContentType 'application/json' | ConvertTo-Json -Depth 6
```

Rate limiting (after 5 quick calls within a minute expect HTTP 429):
```powershell
1..6 | ForEach-Object {
  Invoke-WebRequest -Method Post -Uri http://localhost:8000/process-request `
    -Headers @{ 'X-API-Key'='DEMO-API-KEY-123' } `
    -Body $body -ContentType 'application/json' | Select-Object StatusCode
}
```

## Log Inspection

```powershell
Get-Content .\logs\audit.jsonl | Select-String success
```

Each line: `{ "timestamp": <float>, "phase": "success|error|deny|cache_hit", "request_id": "...", "trace_id": "...", "status": "ok|idempotent-return", "http_status": <code> }` plus step-specific fields.

## Configuration Highlights (`kong.yml`)

- Route: `/process-request` (methods: POST)
- Plugins:
  - `key-auth` (expects `X-API-Key`)
  - `rate-limiting` (`minute: 5`)
  - `chain-plugin` (custom) fields:
    - `policy_service`, `retriever_service`, `processor_service`
    - `log_path`
    - `idempotency_ttl`

## Extending / Next Steps

- Persist idempotency cache using Redis (via Lua resty client) for multi-worker resilience.
- Add OpenAPI/Swagger docs per service.
- Add unit tests (pytest) and contract tests hitting the gateway.
- Enhance summarization with an actual ML/NLP model (e.g., transformers) if required (would require updated dependencies).

## Cleanup

```powershell
docker compose down -v
```

## License

MIT (educational demonstration)
