from fastapi import FastAPI
import os

app = FastAPI(title="Policy Service")

@app.get("/policy")
async def get_policy():
    return {"service": "policy", "policy": "allow", "detail": "Sample policy evaluation"}

@app.get("/health")
async def health():
    return {"status": "ok", "service": os.getenv("SERVICE_NAME", "policy")}
