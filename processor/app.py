from fastapi import FastAPI
import os, httpx

app = FastAPI(title="Processor Service")

@app.get("/process")
async def process():
    # This endpoint may be decorated/augmented by Kong chain plugin; still we can optionally call others directly
    async with httpx.AsyncClient(timeout=2.0) as client:
        policy_resp = await client.get("http://policy:9000/policy")
        retriever_resp = await client.get("http://retriever:9000/retriever")
    return {
        "service": "processor",
        "policy": policy_resp.json(),
        "retrieved": retriever_resp.json(),
        "detail": "Aggregated in processor"
    }

@app.get("/health")
async def health():
    return {"status": "ok", "service": os.getenv("SERVICE_NAME", "processor")}
