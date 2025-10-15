import os
import json
import re
import math
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Retriever Service")

@app.get("/")
@app.get("/docs")
async def welcome():
    return {"message": "Welcome to the Retriever Service!"}

DATASET_PATH = Path(__file__).parent / "dataset.json"
if DATASET_PATH.exists():
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        DATA = json.load(f)
else:
    DATA = []

class RetrieveRequest(BaseModel):
    request_id: str
    query: str

def score(doc_text: str, query: str) -> float:
    q_tokens = set(re.findall(r"\w+", query.lower()))
    if not q_tokens:
        return 0.0
    d_tokens = re.findall(r"\w+", doc_text.lower())
    overlap = sum(1 for t in d_tokens if t in q_tokens)
    return overlap / math.sqrt(len(d_tokens) + 1)

@app.post("/retrieve")
async def retrieve(req: RetrieveRequest):
    if not DATA:
        raise HTTPException(status_code=500, detail="Dataset empty")
    ranked = sorted(
        (
            {
                "id": idx,
                "text": d.get("text", ""),
                "score": score(d.get("text", ""), req.query)
            }
            for idx, d in enumerate(DATA)
        ),
        key=lambda x: x["score"],
        reverse=True
    )
    top3 = [r for r in ranked[:3] if r["score"] > 0]
    return {"service": "retriever", "request_id": req.request_id, "query": req.query, "documents": top3}

@app.get("/health")
async def health():
    return {"status": "ok", "service": os.getenv("SERVICE_NAME", "retriever")}
