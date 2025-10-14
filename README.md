# Microservices with API Gateway Orchestration

This project demonstrates a minimal microservices architecture orchestrated via a Kong API Gateway and a custom Kong plugin (`chain-plugin`) that performs simple service chaining and logging.

## Components

- **Kong Gateway**: Fronts all services, provides routing and runs a custom plugin.
- **policy service** (`/policy`): Returns a sample policy decision.
- **retriever service** (`/retriever`): Returns sample retrieved data.
- **processor service** (`/process`): Aggregates results from the policy and retriever services directly, while the gateway plugin can also pre-fetch them and attach results via a response header.
- **chain-plugin**: Custom Lua plugin that, for configured routes, sequentially calls downstream services and logs the responses to `logs/audit.jsonl`.

## Flow

1. Client calls `KONG /process` endpoint (e.g. `http://localhost:8000/process`).
2. Kong matches the `processor` service route.
3. `chain-plugin` runs in the access phase, calling `/policy` and `/retriever` on their respective upstream containers.
4. Results are stored in `kong.ctx.shared` and a JSON line is appended to `logs/audit.jsonl` inside the gateway container (mounted locally).
5. Upstream `processor` service also performs its own calls (illustrating both gateway-side and service-side composition) and responds.
6. Plugin adds an `X-Chain-Results` header with the aggregated chain call results.

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
│   └── app.py
├── processor/
│   ├── Dockerfile
│   └── app.py
├── logs/
│   └── audit.jsonl
└── README.md
```

## Prerequisites

- Docker + Docker Compose

## Run

Build and start everything:

```powershell
docker compose up --build
```

Wait until Kong reports it is running ("Kong started").

## Test Endpoints

```powershell
# Processor (goes through gateway + plugin)
Invoke-RestMethod http://localhost:8000/process | ConvertTo-Json -Depth 5

# Direct service bypassing gateway (for comparison)
Invoke-RestMethod http://localhost:9003/process | ConvertTo-Json -Depth 5

# Inspect chain header
(Invoke-WebRequest http://localhost:8000/process).Headers['X-Chain-Results']
```

Check the audit log after some requests:

```powershell
Get-Content .\logs\audit.jsonl
```

## Custom Plugin Notes

- Configured in `kong.yml` under the `processor` service route.
- Fields:
  - `chain`: Ordered list of upstream service names to call.
  - `log_path`: File path for JSONL audit log inside container (`/var/log/microservices/audit.jsonl`).
- The plugin adds header `X-Chain-Results` containing a JSON array of the chained calls (status + body).

## Modifying the Chain

Edit `kong.yml` and adjust the `chain` array, then restart Kong:

```powershell
docker compose restart kong
```

## Development Tips

- Add Python deps in `requirements.txt` (shared across the three services for simplicity).
- For iterative gateway plugin development you can restart only the Kong container.

## Cleanup

```powershell
docker compose down -v
```

## License

MIT (sample project)
