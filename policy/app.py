from fastapi import FastAPI
from pydantic import BaseModel
import os, re

app = FastAPI(title="Policy Service")
class PolicyRequest(BaseModel):
    request_id: str
    query: str

@app.post("/policy")
async def get_policy(req: PolicyRequest):
    forbidden = bool(re.search(r"\bforbidden\b", req.query, re.IGNORECASE))
    decision = "deny" if forbidden else "allow"
    return {
        "service": "policy",
        "request_id": req.request_id,
        "policy": decision,
        "detail": "Query contains forbidden term" if forbidden else "OK"
    }

@app.get("/health")
async def health():
    return {"status": "ok", "service": os.getenv("SERVICE_NAME", "policy")}
