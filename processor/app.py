from fastapi import FastAPI
from pydantic import BaseModel
import os, re, hashlib

app = FastAPI(title="Processor Service")

class ProcessRequest(BaseModel):
    request_id: str
    query: str
    documents: list

def summarize(docs, max_sentences=2):
    joined = " ".join(d.get("text", "") for d in docs)
    sentences = re.split(r"(?<=[.!?])\s+", joined)
    return " ".join(sentences[:max_sentences]).strip()

def label(docs):
    text = " ".join(d.get("text", "") for d in docs).lower()
    if "policy" in text:
        return "policy"
    if "gateway" in text or "kong" in text:
        return "infrastructure"
    if "microservice" in text:
        return "architecture"
    return "general"

@app.post("/process")
async def process(req: ProcessRequest):
    summary = summarize(req.documents)
    lbl = label(req.documents)
    digest = hashlib.sha1(summary.encode()).hexdigest()[:8]
    return {
        "service": "processor",
        "request_id": req.request_id,
        "summary": summary,
        "label": lbl,
        "digest": digest
    }

@app.get("/health")
async def health():
    return {"status": "ok", "service": os.getenv("SERVICE_NAME", "processor")}
